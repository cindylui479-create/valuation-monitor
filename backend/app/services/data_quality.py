"""SRS R11：数据异常检测。

检测维度（决策表）：
  A. NEGATIVE          值 < 0                                        HIGH
  B. DAILY_JUMP        |Δ| / yesterday > 0.30                        HIGH
  C. MAD_OUTLIER       |x - rolling_60_median| > 5 × rolling_60_MAD  MEDIUM
  D. STALE             连续 10 天变化 < 0.5%                          MEDIUM
  E. CROSS_DIVERGE     |pe_lg - pe_csi| / pe_lg > 0.30               LOW
  F. CROSS_IDENTICAL   连续 10 天 pe_lg == pe_csi 严格相等             INFO
  G. LOW_VARIANCE      σ(序列, 10y) < 0.5                            HIGH

P1：仅检测落库 + UI 告警，**不修改 temperature/percentile 数值**。
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IndexMeta, IndexQuote
from app.repositories import anomaly_repo
from app.utils.logging import get_logger

log = get_logger("data_quality")

# --- 阈值参数（SRS R11 决策表 v2 — 跑完全量审计后调优） ---
DAILY_JUMP_RATIO = Decimal("0.30")
MAD_WINDOW = 60
MAD_K = Decimal("8")          # v1=5 误报过多（中证500 816 条），PE 长尾分布需更宽松
STALE_WINDOW = 10
STALE_RATIO = Decimal("0.005")
CROSS_DIVERGE_RATIO = Decimal("0.30")
CROSS_IDENTICAL_WINDOW = 10
# LOW_VARIANCE 改用 CV (变异系数 = σ/|μ|)，绝对 σ 在低值 PB 上误报
LOW_VARIANCE_CV_THRESHOLD = Decimal("0.03")  # CV < 3% 视为序列几乎不变

# 字段 → 源 映射
FIELD_SOURCES = (
    ("pe_ttm", "lg"),
    ("pb", "lg"),
    ("pe_ttm_csi", "csi"),
    ("pb_csi", "csi"),
)


@dataclass(frozen=True)
class Finding:
    date: str
    field: str
    source: str
    anomaly_type: str
    severity: str
    value: Decimal | None
    baseline: Decimal | None
    note: str


def detect_for_index(
    session: Session,
    index: IndexMeta,
    *,
    lookback_days: int = 10,
    full_history: bool = False,
) -> list[Finding]:
    """检测单只指数的异常。

    lookback_days: 仅扫最近 N 天（点状检测，用于增量）。
    full_history=True: 全历史扫描（用于一次性审计或 init 后），覆盖 lookback_days。
    """
    quotes = list(
        session.scalars(
            select(IndexQuote)
            .where(IndexQuote.index_id == index.id)
            .order_by(IndexQuote.date.asc())
        )
    )
    if not quotes:
        return []

    findings: list[Finding] = []

    # 全历史扫描：每个字段做一次序列级检查（G）+ 每天做点状检查（A/B/C/D/E/F）
    for field, source in FIELD_SOURCES:
        series = [(q.date, getattr(q, field)) for q in quotes]
        non_null = [(d, v) for d, v in series if v is not None]
        if not non_null:
            continue

        # G. 序列方差异常小（每个字段只产出一条，date 取最后一日）
        if len(non_null) >= 250:
            findings.extend(_check_low_variance(non_null, field, source))

        # 决定点状检测的扫描区间
        if full_history:
            target_dates = {d for d, _ in non_null}
        else:
            target_dates = {d for d, _ in non_null[-lookback_days:]}

        # A. NEGATIVE
        findings.extend(_check_negative(non_null, target_dates, field, source))
        # B. DAILY_JUMP
        findings.extend(_check_daily_jump(non_null, target_dates, field, source))
        # C. MAD_OUTLIER
        findings.extend(_check_mad_outlier(non_null, target_dates, field, source))
        # D. STALE
        findings.extend(_check_stale(non_null, target_dates, field, source))

    # 跨源检查（E、F）：基于 (pe_ttm, pe_ttm_csi) 配对
    pairs_pe = [
        (q.date, q.pe_ttm, q.pe_ttm_csi)
        for q in quotes
        if q.pe_ttm is not None and q.pe_ttm_csi is not None
    ]
    pairs_pb = [
        (q.date, q.pb, q.pb_csi)
        for q in quotes
        if q.pb is not None and q.pb_csi is not None
    ]
    if pairs_pe:
        if full_history:
            target_pe_dates = {d for d, _, _ in pairs_pe}
        else:
            target_pe_dates = {d for d, _, _ in pairs_pe[-lookback_days:]}
        findings.extend(_check_cross_diverge(pairs_pe, target_pe_dates, "pe_ttm_csi"))
        findings.extend(_check_cross_identical(pairs_pe, "pe_ttm_csi"))
    if pairs_pb:
        if full_history:
            target_pb_dates = {d for d, _, _ in pairs_pb}
        else:
            target_pb_dates = {d for d, _, _ in pairs_pb[-lookback_days:]}
        findings.extend(_check_cross_diverge(pairs_pb, target_pb_dates, "pb_csi"))
        findings.extend(_check_cross_identical(pairs_pb, "pb_csi"))

    return findings


# ============ A. NEGATIVE ============
def _check_negative(non_null, target_dates, field, source) -> list[Finding]:
    out = []
    for d, v in non_null:
        if d not in target_dates:
            continue
        if v < 0:
            out.append(Finding(
                date=d, field=field, source=source,
                anomaly_type="NEGATIVE", severity="HIGH",
                value=v, baseline=None,
                note=f"{field}<0：指数整体利润为负，PE 无估值意义",
            ))
    return out


# ============ B. DAILY_JUMP ============
def _check_daily_jump(non_null, target_dates, field, source) -> list[Finding]:
    out = []
    for i in range(1, len(non_null)):
        d, v = non_null[i]
        if d not in target_dates:
            continue
        prev_d, prev_v = non_null[i - 1]
        if prev_v == 0 or prev_v is None:
            continue
        ratio = abs(v - prev_v) / abs(prev_v)
        if ratio > DAILY_JUMP_RATIO:
            out.append(Finding(
                date=d, field=field, source=source,
                anomaly_type="DAILY_JUMP", severity="HIGH",
                value=v, baseline=prev_v,
                note=f"较上一交易日({prev_d}) {prev_v:.3f} 跳变 {float(ratio)*100:.1f}%",
            ))
    return out


# ============ C. MAD_OUTLIER ============
def _check_mad_outlier(non_null, target_dates, field, source) -> list[Finding]:
    out = []
    for i in range(MAD_WINDOW, len(non_null)):
        d, v = non_null[i]
        if d not in target_dates:
            continue
        window_vals = [float(x) for _, x in non_null[i - MAD_WINDOW:i]]
        med = statistics.median(window_vals)
        mad = statistics.median([abs(x - med) for x in window_vals])
        if mad < 1e-9:
            continue  # 数据完全平坦时跳过（由 D 或 G 报）
        deviation = abs(float(v) - med)
        k = Decimal(str(deviation / mad))
        if k > MAD_K:
            out.append(Finding(
                date=d, field=field, source=source,
                anomaly_type="MAD_OUTLIER", severity="MEDIUM",
                value=v, baseline=Decimal(str(med)),
                note=f"偏离 60 日中位数 {med:.3f} 达 {float(k):.1f}×MAD",
            ))
    return out


# ============ D. STALE ============
def _check_stale(non_null, target_dates, field, source) -> list[Finding]:
    out = []
    for i in range(STALE_WINDOW, len(non_null)):
        d, v = non_null[i]
        if d not in target_dates:
            continue
        window = [x for _, x in non_null[i - STALE_WINDOW + 1:i + 1]]
        ref = window[0]
        if ref == 0 or ref is None:
            continue
        max_dev = max(abs(x - ref) / abs(ref) for x in window)
        if max_dev < STALE_RATIO:
            out.append(Finding(
                date=d, field=field, source=source,
                anomaly_type="STALE", severity="MEDIUM",
                value=v, baseline=ref,
                note=f"连续 {STALE_WINDOW} 天变化 < 0.5%（疑似数据冻结）",
            ))
    return out


# ============ E. CROSS_DIVERGE ============
def _check_cross_diverge(pairs, target_dates, field) -> list[Finding]:
    """field 标识被告警的 CSI 字段（pe_ttm_csi / pb_csi），告警关联到 CSI 源。"""
    out = []
    for d, lg_v, csi_v in pairs:
        if d not in target_dates:
            continue
        if lg_v is None or lg_v == 0:
            continue
        ratio = abs(csi_v - lg_v) / abs(lg_v)
        if ratio > CROSS_DIVERGE_RATIO:
            out.append(Finding(
                date=d, field=field, source="csi",
                anomaly_type="CROSS_DIVERGE", severity="LOW",
                value=csi_v, baseline=lg_v,
                note=f"LG={lg_v:.3f} vs CSI={csi_v:.3f}，分歧 {float(ratio)*100:.1f}%",
            ))
    return out


# ============ F. CROSS_IDENTICAL ============
def _check_cross_identical(pairs, field) -> list[Finding]:
    """全序列扫描连续 N 天 LG==CSI 严格相等的区间，产出 INFO 告警（仅落最后一日）。"""
    out = []
    run_start = None
    for i, (d, lg_v, csi_v) in enumerate(pairs):
        if lg_v is not None and csi_v is not None and lg_v == csi_v:
            if run_start is None:
                run_start = i
            # 是否到达终点 or 下一天打破
            is_last = i == len(pairs) - 1
            broke_next = (not is_last) and pairs[i + 1][1] != pairs[i + 1][2]
            if (is_last or broke_next) and (i - run_start + 1) >= CROSS_IDENTICAL_WINDOW:
                length = i - run_start + 1
                out.append(Finding(
                    date=d, field=field, source="csi",
                    anomaly_type="CROSS_IDENTICAL", severity="INFO",
                    value=lg_v, baseline=None,
                    note=f"连续 {length} 天 LG==CSI 严格相等（疑似同源）",
                ))
                run_start = None
        else:
            run_start = None
    return out


# ============ G. LOW_VARIANCE ============
def _check_low_variance(non_null, field, source) -> list[Finding]:
    """用变异系数 CV = σ/|μ| 判定，避免对低均值字段（如 PB）的误报。"""
    vals = [float(v) for _, v in non_null]
    try:
        sd = statistics.stdev(vals)
        mu = statistics.fmean(vals)
    except statistics.StatisticsError:
        return []
    if abs(mu) < 1e-6:
        return []
    cv = sd / abs(mu)
    if Decimal(str(cv)) < LOW_VARIANCE_CV_THRESHOLD:
        last_d = non_null[-1][0]
        return [Finding(
            date=last_d, field=field, source=source,
            anomaly_type="LOW_VARIANCE", severity="HIGH",
            value=Decimal(str(cv)), baseline=Decimal(str(mu)),
            note=f"CV({field}, n={len(vals)}) = {cv*100:.2f}% < 3%（序列几乎不变）",
        )]
    return []


# ============ 落库入口 ============
def persist_findings(session: Session, index_id: int, findings: list[Finding]) -> tuple[int, int]:
    """落库。返回 (new_inserted, refreshed)。"""
    inserted = 0
    refreshed = 0
    for f in findings:
        new = anomaly_repo.upsert(
            session,
            index_id=index_id,
            date_=f.date,
            field=f.field,
            source=f.source,
            anomaly_type=f.anomaly_type,
            severity=f.severity,
            value=f.value,
            baseline=f.baseline,
            note=f.note,
        )
        if new:
            inserted += 1
        else:
            refreshed += 1
    return inserted, refreshed


def detect_and_persist(
    session: Session,
    index: IndexMeta,
    *,
    lookback_days: int = 10,
    full_history: bool = False,
) -> tuple[int, int]:
    findings = detect_for_index(
        session, index,
        lookback_days=lookback_days, full_history=full_history,
    )
    return persist_findings(session, index.id, findings)
