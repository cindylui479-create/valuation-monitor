"""watchlist / threshold-override API 契约测试。"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.deps import db_session
from app.main import create_app
from app.models import IndexMeta, Market


@pytest.fixture
def app_client(engine, monkeypatch):
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    # 阻止 lifespan 启动真实调度器（会用真实 DB）
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "start_scheduler", lambda: None)
    monkeypatch.setattr(main_mod, "shutdown_scheduler", lambda: None)

    app = create_app()
    app.dependency_overrides[db_session] = override_session
    with TestClient(app, raise_server_exceptions=True) as client:
        # seed: 1 market + 1 index
        with SessionLocal() as s:
            m = Market(code="A", name="A 股", currency="CNY", tz="Asia/Shanghai")
            s.add(m); s.flush()
            s.add(IndexMeta(
                code="000300.SH", name="沪深300", market_id=m.id,
                category="宽基", data_source="fake",
                history_start_date="2005-04-08", enabled=True,
            ))
            s.commit()
        yield client


def test_watchlist_crud(app_client):
    # 列表初始空
    r = app_client.get("/api/v1/watchlist")
    assert r.status_code == 200
    assert r.json() == []

    # 加入
    r = app_client.post("/api/v1/watchlist", json={"index_code": "000300.SH", "tag": "核心"})
    assert r.status_code == 201
    wid = r.json()["id"]

    # 列表含一条
    r = app_client.get("/api/v1/watchlist")
    assert len(r.json()) == 1
    assert r.json()[0]["index_code"] == "000300.SH"

    # 重复加入 → 409 / 400
    r = app_client.post("/api/v1/watchlist", json={"index_code": "000300.SH", "tag": "核心"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"

    # 不存在的指数 → 404
    r = app_client.post("/api/v1/watchlist", json={"index_code": "999999.XX"})
    assert r.status_code == 404

    # 删除
    r = app_client.delete(f"/api/v1/watchlist/{wid}")
    assert r.status_code == 204
    r = app_client.get("/api/v1/watchlist")
    assert r.json() == []


def test_threshold_override_default_when_not_set(app_client):
    r = app_client.get("/api/v1/threshold-overrides/000300.SH")
    assert r.status_code == 200
    d = r.json()
    assert d["is_default"] is True
    assert d["boundaries"]["extreme_low_upper"] == "0.10"
    assert d["boundaries"]["low_upper"] == "0.30"


def test_threshold_override_put_get_delete(app_client):
    # 设置
    r = app_client.put(
        "/api/v1/threshold-overrides/000300.SH",
        json={
            "extreme_low_upper": "0.05",
            "low_upper": "0.20",
            "high_lower": "0.75",
            "extreme_high_lower": "0.95",
        },
    )
    assert r.status_code == 200
    assert r.json()["is_default"] is False
    assert r.json()["boundaries"]["low_upper"] == "0.20"

    # 取
    r = app_client.get("/api/v1/threshold-overrides/000300.SH")
    assert r.json()["is_default"] is False
    assert r.json()["boundaries"]["extreme_low_upper"] == "0.05"

    # 删
    r = app_client.delete("/api/v1/threshold-overrides/000300.SH")
    assert r.status_code == 204

    # 再取 → 又回到默认
    r = app_client.get("/api/v1/threshold-overrides/000300.SH")
    assert r.json()["is_default"] is True


def test_threshold_override_validation_unordered(app_client):
    """边界不递增 → 422 validation error。"""
    r = app_client.put(
        "/api/v1/threshold-overrides/000300.SH",
        json={"low_upper": "0.50", "high_lower": "0.40"},  # low > high → invalid
    )
    assert r.status_code == 422


def test_index_detail_includes_funds_and_window_note(app_client):
    r = app_client.get("/api/v1/indices/000300.SH/detail")
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == "000300.SH"
    assert d["market"] == "A"
    assert d["currency"] == "CNY"
    assert d["funds"] == []  # 测试 fixture 没 seed 基金
    # 没 quotes → actual_history_years 0，window note 是 "< 5 年"
    assert d["actual_history_years"] == 0.0
    assert d["data_window_note"] is not None
    assert d["quotes"] == []
    assert d["valuation_series"] == []
