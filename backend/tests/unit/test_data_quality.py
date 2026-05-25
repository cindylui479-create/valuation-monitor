"""SRS R11：数据异常检测器单测。

每个 anomaly_type 一个测试场景，覆盖正向触发与反向不触发两类。
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import IndexMeta, IndexQuote, Market
from app.services.data_quality import (
    detect_for_index,
    detect_and_persist,
)


@pytest.fixture
def a_index(session):
    m = Market(code="A", name="A股", currency="CNY", tz="Asia/Shanghai")
    session.add(m); session.flush()
    idx = IndexMeta(
        code="000300.SH", name="沪深300", market_id=m.id, category="宽基",
        data_source="akshare", history_start_date="2005-04-08", enabled=True,
    )
    session.add(idx); session.commit()
    return idx


def _add_quote(session, idx, d, *, pe=None, pb=None, pe_csi=None, pb_csi=None):
    session.add(IndexQuote(
        index_id=idx.id, date=d, close=Decimal("4000"),
        pe_ttm=Decimal(str(pe)) if pe is not None else None,
        pb=Decimal(str(pb)) if pb is not None else None,
        pe_ttm_csi=Decimal(str(pe_csi)) if pe_csi is not None else None,
        pb_csi=Decimal(str(pb_csi)) if pb_csi is not None else None,
        source="test", created_at="2026-05-18T00:00:00Z",
    ))


def _days(n):
    today = date.today()
    return [(today - timedelta(days=n - 1 - i)).isoformat() for i in range(n)]


# ============ A. NEGATIVE ============
def test_negative_triggers(session, a_index):
    days = _days(3)
    _add_quote(session, a_index, days[0], pe=10)
    _add_quote(session, a_index, days[1], pe=-5)
    _add_quote(session, a_index, days[2], pe=8)
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    types = {(f.anomaly_type, f.date) for f in findings}
    assert ("NEGATIVE", days[1]) in types


def test_negative_only_in_lookback(session, a_index):
    days = _days(15)
    for i, d in enumerate(days):
        _add_quote(session, a_index, d, pe=-1 if i == 0 else 10)  # 负值在第一天，应不在最近10天内
    session.commit()
    findings = detect_for_index(session, a_index, lookback_days=10)
    assert not any(f.anomaly_type == "NEGATIVE" for f in findings)


# ============ B. DAILY_JUMP ============
def test_daily_jump_triggers(session, a_index):
    days = _days(3)
    _add_quote(session, a_index, days[0], pe=10)
    _add_quote(session, a_index, days[1], pe=10.05)   # +0.5% OK
    _add_quote(session, a_index, days[2], pe=14)       # +39% 触发
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    jump = [f for f in findings if f.anomaly_type == "DAILY_JUMP"]
    assert len(jump) == 1
    assert jump[0].date == days[2]
    assert jump[0].severity == "HIGH"


def test_daily_jump_not_triggered_small_move(session, a_index):
    days = _days(3)
    _add_quote(session, a_index, days[0], pe=10)
    _add_quote(session, a_index, days[1], pe=11)       # +10% OK
    _add_quote(session, a_index, days[2], pe=10.5)    # -4.5% OK
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    assert not any(f.anomaly_type == "DAILY_JUMP" for f in findings)


# ============ C. MAD_OUTLIER ============
def test_mad_outlier_triggers(session, a_index):
    days = _days(65)
    # 前 60 天围绕 10 在 ±0.5 抖动
    for i in range(60):
        _add_quote(session, a_index, days[i], pe=10 + (0.5 if i % 2 else -0.5))
    # 第 61 天突然 30（极端偏离）
    _add_quote(session, a_index, days[60], pe=30)
    for i in range(61, 65):
        _add_quote(session, a_index, days[i], pe=10)
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    mad = [f for f in findings if f.anomaly_type == "MAD_OUTLIER"]
    assert any(f.date == days[60] for f in mad)


# ============ D. STALE ============
def test_stale_triggers(session, a_index):
    days = _days(15)
    # 前 5 天有变化
    for i in range(5):
        _add_quote(session, a_index, days[i], pe=10 + i)
    # 后 10 天完全相同（10）
    for i in range(5, 15):
        _add_quote(session, a_index, days[i], pe=10)
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    stale = [f for f in findings if f.anomaly_type == "STALE"]
    assert stale, "10 连日 PE 相同应触发 STALE"


# ============ E. CROSS_DIVERGE ============
def test_cross_diverge_triggers(session, a_index):
    days = _days(3)
    _add_quote(session, a_index, days[0], pe=10, pe_csi=10.5)   # 5% OK
    _add_quote(session, a_index, days[1], pe=10, pe_csi=15)      # 50% 触发
    _add_quote(session, a_index, days[2], pe=10, pe_csi=11)
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    div = [f for f in findings if f.anomaly_type == "CROSS_DIVERGE"]
    assert any(f.date == days[1] for f in div)


# ============ F. CROSS_IDENTICAL ============
def test_cross_identical_triggers(session, a_index):
    days = _days(12)
    for i in range(12):
        v = Decimal("17.53")
        _add_quote(session, a_index, days[i], pe=v, pe_csi=v)
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    iden = [f for f in findings if f.anomaly_type == "CROSS_IDENTICAL"]
    assert iden, "12 连日 LG==CSI 严格相等应触发 CROSS_IDENTICAL"
    assert iden[0].severity == "INFO"


def test_cross_identical_short_run_not_triggered(session, a_index):
    days = _days(5)
    for i, d in enumerate(days):
        v = Decimal("17.53")
        _add_quote(session, a_index, d, pe=v, pe_csi=v)
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    assert not any(f.anomaly_type == "CROSS_IDENTICAL" for f in findings)


# ============ G. LOW_VARIANCE ============
def test_low_variance_triggers(session, a_index):
    days = _days(260)
    for i, d in enumerate(days):
        _add_quote(session, a_index, d, pe=Decimal("10.00"))  # 完全平坦
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    lv = [f for f in findings if f.anomaly_type == "LOW_VARIANCE"]
    assert lv, "260 个完全相同的 PE 值应触发 LOW_VARIANCE"
    assert lv[0].severity == "HIGH"


def test_low_variance_not_triggered_normal_series(session, a_index):
    days = _days(260)
    for i, d in enumerate(days):
        _add_quote(session, a_index, d, pe=Decimal("10") + Decimal(i % 5))
    session.commit()
    findings = detect_for_index(session, a_index, full_history=True)
    assert not any(f.anomaly_type == "LOW_VARIANCE" for f in findings)


# ============ acknowledge ============
def test_acknowledge_toggle(session, a_index):
    from app.repositories import anomaly_repo

    days = _days(3)
    _add_quote(session, a_index, days[0], pe=10)
    _add_quote(session, a_index, days[1], pe=-5)
    _add_quote(session, a_index, days[2], pe=10)
    session.commit()
    detect_and_persist(session, a_index, full_history=True)
    session.commit()

    # 任取一条
    row = anomaly_repo.list_for_index(session, a_index.id)[0]
    assert row.acknowledged_at is None

    # 标记
    updated = anomaly_repo.set_acknowledged(
        session, row.id, ack=True, note="2018 商誉减值已查证"
    )
    session.commit()
    assert updated.acknowledged_at is not None
    assert updated.acknowledged_note == "2018 商誉减值已查证"

    # 取消标记
    updated = anomaly_repo.set_acknowledged(session, row.id, ack=False)
    session.commit()
    assert updated.acknowledged_at is None
    assert updated.acknowledged_note is None


def test_counts_excludes_acknowledged(session, a_index):
    from app.repositories import anomaly_repo

    days = _days(3)
    _add_quote(session, a_index, days[0], pe=10)
    _add_quote(session, a_index, days[1], pe=-5)
    _add_quote(session, a_index, days[2], pe=10)
    session.commit()
    detect_and_persist(session, a_index, full_history=True)
    session.commit()

    counts_all = anomaly_repo.counts_by_index_severity(session, include_acknowledged=True)
    total_all = sum(counts_all.get(a_index.id, {}).values())
    assert total_all > 0

    # 标记所有
    for row in anomaly_repo.list_for_index(session, a_index.id):
        anomaly_repo.set_acknowledged(session, row.id, ack=True)
    session.commit()

    counts_unack = anomaly_repo.counts_by_index_severity(session, include_acknowledged=False)
    assert sum(counts_unack.get(a_index.id, {}).values()) == 0

    ack_counts = anomaly_repo.counts_acknowledged_by_index(session)
    assert ack_counts.get(a_index.id, 0) == total_all


# ============ persist ============
def test_persist_upsert_dedup(session, a_index):
    days = _days(3)
    _add_quote(session, a_index, days[0], pe=10)
    _add_quote(session, a_index, days[1], pe=-5)
    _add_quote(session, a_index, days[2], pe=10)
    session.commit()
    n1, r1 = detect_and_persist(session, a_index, full_history=True)
    session.commit()
    assert n1 >= 1 and r1 == 0
    # 再跑一次：所有 finding 都该是 refresh，不新增
    n2, r2 = detect_and_persist(session, a_index, full_history=True)
    session.commit()
    assert n2 == 0
    assert r2 >= 1
