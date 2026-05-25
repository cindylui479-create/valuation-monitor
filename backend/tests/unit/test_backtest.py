"""回测引擎单元测试（M5 / SRS D9）。"""
from __future__ import annotations

from decimal import Decimal

from app.services.backtest_runner import _annualized, _max_drawdown, run_backtest


def D(s: str) -> Decimal:
    return Decimal(s)


def test_annualized_doubling_over_one_year():
    """NAV 1 → 2，一年 → 年化约 +100%。"""
    curve = [("2024-01-01", D("1")), ("2025-01-01", D("2"))]
    r = _annualized(curve)
    assert D("0.99") < r < D("1.01"), f"expected ~1.0, got {r}"


def test_annualized_zero_for_flat_curve():
    curve = [("2024-01-01", D("1")), ("2025-01-01", D("1"))]
    assert _annualized(curve) == D("0")


def test_max_drawdown_simple_v_shape():
    """NAV 1 → 2 → 1 → 1.5：峰 2，谷 1 → 回撤 -50%。"""
    curve = [
        ("2024-01-01", D("1")),
        ("2024-06-01", D("2")),
        ("2024-09-01", D("1")),
        ("2025-01-01", D("1.5")),
    ]
    assert _max_drawdown(curve) == D("-0.500000")


def test_max_drawdown_monotonic_up_is_zero():
    curve = [(f"2024-01-{i:02d}", D(str(1 + i / 10))) for i in range(1, 10)]
    assert _max_drawdown(curve) == D("0")


def test_buy_low_sell_high_one_round_trip():
    """构造数据：分位先 0.10（买入），后 0.90（卖出），价格 100 → 200。"""
    quotes = [
        ("2024-01-01", D("100")),
        ("2024-06-01", D("150")),
        ("2024-12-01", D("200")),
    ]
    percentiles = {
        "2024-01-01": D("0.10"),
        "2024-06-01": D("0.50"),
        "2024-12-01": D("0.90"),
    }
    res = run_backtest(
        index_code="TEST",
        quotes=quotes,
        percentiles=percentiles,
        buy_below=D("0.20"),
        sell_above=D("0.80"),
        start="2024-01-01",
        end="2024-12-01",
        include_dca=False,
    )
    th = res.threshold
    assert th.trade_count == 2
    assert th.trades[0].action == "BUY" and th.trades[0].price == D("100")
    assert th.trades[1].action == "SELL" and th.trades[1].price == D("200")
    assert th.final_nav == D("2")
    # buy_hold 基准：起始 100 持有到末日 200 → final NAV = 2
    assert res.buy_hold.final_nav == D("2")


def test_no_signal_in_fair_range_keeps_cash():
    """全程分位在 0.30~0.70 → 无任何交易，最终 NAV = 1（持币不动）。"""
    quotes = [
        ("2024-01-01", D("100")),
        ("2024-06-01", D("150")),
        ("2024-12-01", D("200")),
    ]
    percentiles = {d: D("0.50") for d, _ in quotes}
    res = run_backtest("TEST", quotes, percentiles,
                       buy_below=D("0.20"), sell_above=D("0.80"),
                       start="2024-01-01", end="2024-12-01", include_dca=False)
    assert res.threshold.trade_count == 0
    assert res.threshold.final_nav == D("1")


def test_holding_through_end_marks_to_final_close():
    """买入后未触发卖出 → 持有到末日，NAV 按末日收盘计算。"""
    quotes = [
        ("2024-01-01", D("100")),
        ("2024-06-01", D("150")),
        ("2024-12-01", D("180")),  # 仍未到 0.90
    ]
    percentiles = {
        "2024-01-01": D("0.10"),
        "2024-06-01": D("0.40"),
        "2024-12-01": D("0.60"),
    }
    res = run_backtest("TEST", quotes, percentiles,
                       buy_below=D("0.20"), sell_above=D("0.80"),
                       start="2024-01-01", end="2024-12-01", include_dca=False)
    assert res.threshold.trade_count == 1
    assert res.threshold.trades[0].action == "BUY"
    # 持仓 0.01 股 → 末日 NAV = 0 + 0.01 × 180 = 1.80
    assert res.threshold.final_nav == D("1.80")


# ---------- M5 BT 扩展 ----------

def test_fee_and_slippage_reduce_final_nav():
    """100 → 200 一次买卖；手续费 0.1% + 滑点 0.1% 应该让 final NAV < 2。"""
    quotes = [
        ("2024-01-01", D("100")),
        ("2024-12-01", D("200")),
    ]
    percentiles = {"2024-01-01": D("0.10"), "2024-12-01": D("0.90")}
    res = run_backtest("T", quotes, percentiles, D("0.20"), D("0.80"),
                       "2024-01-01", "2024-12-01",
                       fee_rate=D("0.001"), slippage_rate=D("0.001"),
                       include_dca=False)
    th = res.threshold
    # 含手续费滑点后应 < 2.0（裸 NAV 是 2.0），且差距在 1% 内
    assert D("1.99") < th.final_nav < D("2.0"), th.final_nav


def test_buy_hold_baseline_doubles_with_2x_price():
    quotes = [("2024-01-01", D("100")), ("2024-12-01", D("200"))]
    percentiles = {"2024-01-01": D("0.50"), "2024-12-01": D("0.50")}
    res = run_backtest("T", quotes, percentiles, D("0.20"), D("0.80"),
                       "2024-01-01", "2024-12-01", include_dca=False)
    assert res.buy_hold.final_nav == D("2")
    assert res.threshold.final_nav == D("1")  # 阈值策略未触发


def test_dca_monthly_accumulates_holdings():
    """每月首交易日买入；3 个月每月投 1.0（multiplier=1.0 因为 boundaries=None）。
    最终 NAV = 持仓市值 / 投入 = (3 月累计买入的 shares × 末日 close) / 3。
    简单验证：投入 3 次，shares > 0。"""
    quotes = []
    for m in range(1, 13):
        # 每月 1 日
        quotes.append((f"2024-{m:02d}-01", D("100")))
    percentiles = {d: D("0.50") for d, _ in quotes}
    res = run_backtest("T", quotes, percentiles, D("0.20"), D("0.80"),
                       "2024-01-01", "2024-12-01", include_dca=True)
    assert res.dca is not None
    assert res.dca.trade_count == 12
    # 全部按 close=100 买入，每次投 1 块 → 12 次 → 0.12 shares
    # 末日市值 = 0.12 × 100 = 12；总投入 12 → NAV = 1.0
    assert abs(float(res.dca.final_nav) - 1.0) < 0.01


def test_dca_multiplier_doubles_invest_at_low_pe():
    """分位低时（multiplier=2.0）投入更多，分位高时（multiplier=0.5）少；
    需要 boundaries 才能区分档位。"""
    quotes = [(f"2024-{m:02d}-01", D("100")) for m in range(1, 4)]  # 3 个月
    # 月 1 极度低估，月 2 合理，月 3 极度高估
    percentiles = {
        "2024-01-01": D("0.05"),  # mul=2.0
        "2024-02-01": D("0.50"),  # mul=1.0
        "2024-03-01": D("0.95"),  # mul=0.0
    }
    boundaries = {
        "extreme_low_upper": D("0.10"),
        "low_upper": D("0.30"),
        "high_lower": D("0.70"),
        "extreme_high_lower": D("0.90"),
    }
    res = run_backtest("T", quotes, percentiles, D("0.20"), D("0.80"),
                       "2024-01-01", "2024-03-01",
                       include_dca=True, dca_boundaries=boundaries)
    assert res.dca is not None
    # 应该有 2 笔成交（月 1 ×2 + 月 2 ×1），月 3 mul=0 不交易
    assert res.dca.trade_count == 2
    assert res.dca.trades[0].multiplier == D("2.0")
    assert res.dca.trades[1].multiplier == D("1.0")


def test_dividend_reinvest_increases_buy_hold_nav():
    """构造 1 年 close 不变（100→100）+ 每日 2% 年化股息率 → buy_hold NAV 应略高于 1。"""
    quotes = [(f"2024-{m:02d}-01", D("100")) for m in range(1, 13)]
    # 加一天末日
    quotes.append(("2024-12-31", D("100")))
    percentiles = {d: D("0.50") for d, _ in quotes}
    dy = {d: D("0.02") for d, _ in quotes}  # 2% 年化
    res = run_backtest("T", quotes, percentiles, D("0.20"), D("0.80"),
                       "2024-01-01", "2024-12-31",
                       reinvest_dividend=True, dividend_yields=dy,
                       include_dca=False)
    # 不开分红 → NAV = 1（close 不变）；开了 → 应 > 1
    assert res.buy_hold.final_nav > D("1.00")


def test_buy_hold_has_nav_curve():
    quotes = [(f"2024-{m:02d}-01", D("100") + D(m * 10)) for m in range(1, 13)]
    percentiles = {d: D("0.50") for d, _ in quotes}
    res = run_backtest("T", quotes, percentiles, D("0.20"), D("0.80"),
                       "2024-01-01", "2024-12-01", include_dca=False)
    assert len(res.buy_hold.nav_curve) == 12
    assert len(res.threshold.nav_curve) == 12
    assert res.buy_hold.nav_curve[0].date == "2024-01-01"
    assert res.buy_hold.nav_curve[-1].date == "2024-12-01"
