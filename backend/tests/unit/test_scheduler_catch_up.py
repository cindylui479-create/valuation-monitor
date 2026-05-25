"""SCH-2：服务启动时漏跑补跑逻辑测试（SRS R9）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.scheduler.runner import _should_catch_up


def test_catch_up_when_no_data():
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    assert _should_catch_up(None, now, threshold_hours=30) is True


def test_no_catch_up_when_recent():
    """3 小时前入库 → 不需补跑。"""
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    last = (now - timedelta(hours=3)).isoformat()
    assert _should_catch_up(last, now, threshold_hours=30) is False


def test_catch_up_when_stale_beyond_threshold():
    """40 小时前 > 30 小时阈值 → 补跑。"""
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    last = (now - timedelta(hours=40)).isoformat()
    assert _should_catch_up(last, now, threshold_hours=30) is True


def test_threshold_boundary_not_triggered():
    """正好 30 小时（boundary）→ 不触发；只严格 > 才补跑。"""
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    last = (now - timedelta(hours=30)).isoformat()
    assert _should_catch_up(last, now, threshold_hours=30) is False


def test_naive_iso_treated_as_utc():
    """无时区后缀的 ISO（旧 now_iso 行为）也能正确解析为 UTC。"""
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    last = "2026-05-15T12:00:00"  # 70+ 小时前，naive
    assert _should_catch_up(last, now, threshold_hours=30) is True


def test_invalid_iso_triggers_catch_up():
    """损坏的时间戳 → 安全起见触发补跑（避免漏更新）。"""
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    assert _should_catch_up("not-a-date", now, threshold_hours=30) is True
