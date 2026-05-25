"""SRS v1.3.0 EFF：温度有效性分析。

核心问题：温度真的能预测未来收益吗？

方法：把每只指数每个交易日当一个数据点 — 取当日 temperature + close，
计算 +N 天后的 close，得到未来收益率。按温度档位分桶聚合。

如果"温度有效性"假设成立，应该看到：
- 极度低估桶 → 未来收益中位数高
- 极度高估桶 → 未来收益中位数低（甚至为负）
- 单调相关

如果各桶未来收益差不多，说明温度作为预测工具没用。
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import IndexMeta, IndexQuote, Valuation

router = APIRouter()


# 标准 5 档位（上界开放区间，100 也算极度高估）
TIER_RANGES = [
    ("极度低估", 0, 10),
    ("低估", 10, 30),
    ("合理", 30, 70),
    ("高估", 70, 90),
    ("极度高估", 90, 101),
]


def _bucket_label(temp: float) -> str:
    if temp < 10: return "极度低估"
    if temp < 30: return "低估"
    if temp < 70: return "合理"
    if temp < 90: return "高估"
    return "极度高估"


class BucketStats(BaseModel):
    tier: str
    temp_range: str           # "0-10"
    n_samples: int
    median_return_pct: str | None
    mean_return_pct: str | None
    p25: str | None
    p75: str | None
    p10: str | None
    p90: str | None
    win_rate: str | None      # 收益 > 0 的占比


class FineBucketPoint(BaseModel):
    """10 度细分 bucket（散点用）。"""
    temp_center: int          # 5, 15, 25, ..., 95
    n_samples: int
    median_return_pct: str | None


class IndexCoverage(BaseModel):
    """单指数覆盖情况（样本量）。"""
    code: str
    name: str
    n_samples: int


class IndexEffectiveness(BaseModel):
    """单指数温度有效性聚合（SRS v1.3.0 C 新增）。"""
    code: str
    name: str
    n_samples: int
    spearman_ic: str | None             # 温度 vs 未来收益的 Spearman 相关系数
    low_temp_median_return: str | None  # 温度 < 30 桶
    high_temp_median_return: str | None # 温度 >= 70 桶
    edge_pct: str | None                # high - low（理想为负 — 越负说明"低买高卖"越有效）


class EffectivenessResponse(BaseModel):
    horizon_days: int
    years: int
    scope: str                          # 'all' or 指数代码
    total_samples: int
    coarse_buckets: list[BucketStats]   # 5 档位
    fine_buckets: list[FineBucketPoint] # 10 个细分（每 10 度一个）
    indices_coverage: list[IndexCoverage]
    # SRS v1.3.0 C：
    spearman_ic: str | None             # 全局 IC
    by_index_effectiveness: list[IndexEffectiveness]


def _pct(idx: int, n: int) -> int:
    return max(0, min(n - 1, idx))


def _percentile(sorted_arr: list[float], p: float) -> float:
    n = len(sorted_arr)
    idx = int(p / 100 * (n - 1))
    return sorted_arr[_pct(idx, n)]


def _aggregate(returns: list[float]) -> dict:
    if not returns:
        return {"n": 0}
    s = sorted(returns)
    return {
        "n": len(returns),
        "median": statistics.median(returns),
        "mean": statistics.fmean(returns),
        "p10": _percentile(s, 10),
        "p25": _percentile(s, 25),
        "p75": _percentile(s, 75),
        "p90": _percentile(s, 90),
        "win_rate": sum(1 for r in returns if r > 0) / len(returns) * 100,
    }


def _format_pct(v: float | None, digits: int = 2) -> str | None:
    if v is None:
        return None
    return f"{v:.{digits}f}"


@router.get("/temperature/effectiveness", response_model=EffectivenessResponse)
def temperature_effectiveness(
    horizon: int = Query(default=90, ge=7, le=730),
    years: int = Query(default=10, ge=1, le=20),
    index_code: str | None = Query(default=None),
    session: Session = Depends(db_session),
) -> EffectivenessResponse:
    cutoff = (date.today() - timedelta(days=years * 365)).isoformat()

    # 1) 拉所有 valuation × quote（按 index_id, date join）
    indices_q = select(IndexMeta).where(IndexMeta.enabled == True)  # noqa: E712
    if index_code:
        indices_q = indices_q.where(IndexMeta.code == index_code)
    indices = list(session.scalars(indices_q))

    coverage_by_index: dict[str, IndexCoverage] = {}
    returns_by_coarse: dict[str, list[float]] = {label: [] for label, _, _ in TIER_RANGES}
    returns_by_fine: dict[int, list[float]] = {i: [] for i in range(0, 100, 10)}
    # SRS v1.3.0 C：全局和单指数级别的 (temp, return) 配对，用于算 Spearman IC
    global_pairs: list[tuple[float, float]] = []
    per_index_pairs: dict[str, list[tuple[float, float]]] = {}
    per_index_meta: dict[str, str] = {}  # code → name
    total = 0

    for idx in indices:
        # 拉这个指数的所有 (date, temperature, close)
        rows = session.execute(
            select(IndexQuote.date, IndexQuote.close, Valuation.temperature)
            .join(Valuation, (Valuation.index_id == IndexQuote.index_id)
                  & (Valuation.date == IndexQuote.date)
                  & (Valuation.window == "10y")
                  & (Valuation.source == "lg"))
            .where(IndexQuote.index_id == idx.id)
            .where(IndexQuote.date >= cutoff)
            .where(Valuation.temperature.is_not(None))
            .order_by(IndexQuote.date.asc())
        ).all()

        if not rows:
            continue

        # 建 close 索引（forward-fill 用）
        closes: dict[str, Decimal] = {r[0]: r[1] for r in rows}
        sorted_dates = sorted(closes.keys())

        n_idx = 0
        for d, entry_close, temp in rows:
            future = (date.fromisoformat(d) + timedelta(days=horizon)).isoformat()
            # 找 future 当日或之后最近的 close
            future_close = closes.get(future)
            if future_close is None:
                # 从 sorted_dates 找 >= future 的最近
                from bisect import bisect_left
                pos = bisect_left(sorted_dates, future)
                if pos >= len(sorted_dates):
                    continue
                future_close = closes[sorted_dates[pos]]
            if entry_close == 0:
                continue
            ret_pct = float((future_close - entry_close) / entry_close * 100)
            t = float(temp)
            label = _bucket_label(t)
            returns_by_coarse[label].append(ret_pct)
            fine_key = min(90, int(t // 10) * 10)
            returns_by_fine[fine_key].append(ret_pct)
            global_pairs.append((t, ret_pct))
            per_index_pairs.setdefault(idx.code, []).append((t, ret_pct))
            n_idx += 1
            total += 1

        coverage_by_index[idx.code] = IndexCoverage(
            code=idx.code, name=idx.name, n_samples=n_idx,
        )
        per_index_meta[idx.code] = idx.name

    # 2) 聚合 5 档位
    coarse_results: list[BucketStats] = []
    for label, lo, hi in TIER_RANGES:
        rets = returns_by_coarse[label]
        agg = _aggregate(rets)
        if agg["n"] == 0:
            coarse_results.append(BucketStats(
                tier=label, temp_range=f"{lo}-{hi if hi != 101 else 100}",
                n_samples=0,
                median_return_pct=None, mean_return_pct=None,
                p25=None, p75=None, p10=None, p90=None, win_rate=None,
            ))
        else:
            coarse_results.append(BucketStats(
                tier=label, temp_range=f"{lo}-{hi if hi != 101 else 100}",
                n_samples=agg["n"],
                median_return_pct=_format_pct(agg["median"]),
                mean_return_pct=_format_pct(agg["mean"]),
                p25=_format_pct(agg["p25"]),
                p75=_format_pct(agg["p75"]),
                p10=_format_pct(agg["p10"]),
                p90=_format_pct(agg["p90"]),
                win_rate=_format_pct(agg["win_rate"], 1),
            ))

    # 3) 10 度细分
    fine_results: list[FineBucketPoint] = []
    for lo in sorted(returns_by_fine.keys()):
        rets = returns_by_fine[lo]
        center = lo + 5
        if rets:
            fine_results.append(FineBucketPoint(
                temp_center=center, n_samples=len(rets),
                median_return_pct=_format_pct(statistics.median(rets)),
            ))
        else:
            fine_results.append(FineBucketPoint(
                temp_center=center, n_samples=0, median_return_pct=None,
            ))

    # SRS v1.3.0 C：算 Spearman IC（温度 vs 未来收益的秩相关）
    def _spearman(pairs: list[tuple[float, float]]) -> float | None:
        if len(pairs) < 10:
            return None
        # 用 statistics 内置 — Python 3.10+ 有 correlation
        try:
            xs = [p[0] for p in pairs]
            ys = [p[1] for p in pairs]
            # 转秩
            def _ranks(arr):
                pairs_idx = sorted(range(len(arr)), key=lambda i: arr[i])
                ranks = [0.0] * len(arr)
                for r, i in enumerate(pairs_idx):
                    ranks[i] = r + 1
                return ranks
            rx = _ranks(xs)
            ry = _ranks(ys)
            return statistics.correlation(rx, ry)
        except Exception:
            return None

    global_ic = _spearman(global_pairs)

    # 单指数有效性
    by_idx: list[IndexEffectiveness] = []
    for code, pairs in per_index_pairs.items():
        if len(pairs) < 50:
            continue  # 样本太少跳过
        low_returns = [r for t, r in pairs if t < 30]
        high_returns = [r for t, r in pairs if t >= 70]
        low_med = statistics.median(low_returns) if low_returns else None
        high_med = statistics.median(high_returns) if high_returns else None
        edge = (high_med - low_med) if (low_med is not None and high_med is not None) else None
        ic = _spearman(pairs)
        by_idx.append(IndexEffectiveness(
            code=code,
            name=per_index_meta[code],
            n_samples=len(pairs),
            spearman_ic=_format_pct(ic, 4) if ic is not None else None,
            low_temp_median_return=_format_pct(low_med) if low_med is not None else None,
            high_temp_median_return=_format_pct(high_med) if high_med is not None else None,
            edge_pct=_format_pct(edge) if edge is not None else None,
        ))
    # 按 |IC| 降序排（最有"信号"的指数在前）
    by_idx.sort(key=lambda b: -abs(float(b.spearman_ic) if b.spearman_ic else 0))

    return EffectivenessResponse(
        horizon_days=horizon,
        years=years,
        scope=index_code or "all",
        total_samples=total,
        coarse_buckets=coarse_results,
        fine_buckets=fine_results,
        indices_coverage=sorted(coverage_by_index.values(), key=lambda c: -c.n_samples),
        spearman_ic=_format_pct(global_ic, 4) if global_ic is not None else None,
        by_index_effectiveness=by_idx,
    )
