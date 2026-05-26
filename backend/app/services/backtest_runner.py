"""回测引擎（SRS FR-6 + D9 + M5 扩展）。

三策略并行：
  - threshold : 单一阈值（PE 百分位 < buy 全仓买、> sell 全仓卖）
  - dca       : 定投策略（每月首个交易日按 multiplier 加仓；联动 boundaries）
  - buy_hold  : 起始日全仓买入持有到末日（基准）

可选参数：
  - fee_rate         : 单边手续费率（0.001 = 0.1%）
  - slippage_rate    : 滑点（按当日 close 的百分比）
  - reinvest_dividend: 是否分红再投资（依赖 dividend_yield 历史）

输出：每个策略含 NAV 曲线 + 年化 + 最大回撤 + 交易明细。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Trade:
    date: str
    action: str
    price: Decimal
    pe_percentile: Decimal | None
    amount: Decimal
    multiplier: Decimal | None = None


@dataclass
class NAVPoint:
    date: str
    nav: Decimal


@dataclass
class StrategyResult:
    name: str
    annualized_return: Decimal
    max_drawdown: Decimal
    final_nav: Decimal
    trade_count: int
    trades: list[Trade] = field(default_factory=list)
    nav_curve: list[NAVPoint] = field(default_factory=list)


@dataclass
class BacktestResult:
    index_code: str
    start_date: str
    end_date: str
    buy_percentile_below: Decimal
    sell_percentile_above: Decimal
    fee_rate: Decimal
    slippage_rate: Decimal
    reinvest_dividend: bool
    threshold: StrategyResult
    dca: StrategyResult | None
    buy_hold: StrategyResult
    # SRS v1.3.0 B：按温度档位调仓策略
    by_temperature: StrategyResult | None = None


# ---------- 工具 ----------

def _apply_buy_cost(
    cash: Decimal, price: Decimal, fee: Decimal, slip: Decimal
) -> tuple[Decimal, Decimal]:
    """返回 (shares_bought, cash_left)。买入价 = price × (1 + slip)；扣 fee。"""
    effective_price = price * (Decimal(1) + slip)
    if effective_price <= 0:
        return Decimal(0), cash
    gross = cash * (Decimal(1) - fee)
    shares = gross / effective_price
    return shares, Decimal(0)


def _apply_sell_cost(
    shares: Decimal, price: Decimal, fee: Decimal, slip: Decimal
) -> tuple[Decimal, Decimal]:
    """返回 (cash_received, shares_left)。卖出价 = price × (1 - slip)；扣 fee。"""
    effective_price = price * (Decimal(1) - slip)
    gross = shares * effective_price
    cash = gross * (Decimal(1) - fee)
    return cash, Decimal(0)


def _reinvest_dividend(
    shares: Decimal, close: Decimal, dy: Decimal | None, days_gap: int
) -> Decimal:
    """简化模型：dy 是年化股息率，按交易日比例加到 shares。返回新增 shares。"""
    if dy is None or close <= 0 or shares <= 0:
        return Decimal(0)
    daily_div = shares * close * dy * Decimal(max(1, days_gap)) / Decimal(252)
    return daily_div / close


# ---------- 各策略 ----------

def _run_threshold(
    quotes, percentiles, buy_below, sell_above,
    fee, slip, div_yields, reinvest_div,
) -> StrategyResult:
    cash, shares = Decimal(1), Decimal(0)
    trades: list[Trade] = []
    nav: list[NAVPoint] = []
    holding = False
    prev_d: date | None = None
    for d, close in quotes:
        if close <= 0:
            continue
        cur_d = date.fromisoformat(d)
        if reinvest_div and holding and prev_d is not None:
            shares += _reinvest_dividend(shares, close, div_yields.get(d), (cur_d - prev_d).days)
        p = percentiles.get(d)
        nav.append(NAVPoint(date=d, nav=cash + shares * close))
        prev_d = cur_d
        if p is None:
            continue
        if not holding and p < buy_below:
            new_shares, cash_left = _apply_buy_cost(cash, close, fee, slip)
            shares += new_shares
            cash = cash_left
            holding = True
            trades.append(Trade(d, "BUY", close, p, amount=Decimal(1)))
        elif holding and p > sell_above:
            new_cash, _ = _apply_sell_cost(shares, close, fee, slip)
            cash += new_cash
            shares = Decimal(0)
            holding = False
            trades.append(Trade(d, "SELL", close, p, amount=new_cash))
    return _finalize("threshold", nav, trades)


def _run_buy_hold(quotes, fee, slip, div_yields, reinvest_div) -> StrategyResult:
    if not quotes:
        return StrategyResult(name="buy_hold", annualized_return=Decimal(0),
                              max_drawdown=Decimal(0), final_nav=Decimal(1),
                              trade_count=0)
    cash = Decimal(1)
    shares = Decimal(0)
    nav: list[NAVPoint] = []
    trades: list[Trade] = []
    first_d, first_close = quotes[0]
    if first_close > 0:
        shares, cash = _apply_buy_cost(cash, first_close, fee, slip)
        trades.append(Trade(first_d, "BUY", first_close, None, amount=Decimal(1)))
    prev_d: date | None = date.fromisoformat(first_d)
    for d, close in quotes:
        cur_d = date.fromisoformat(d)
        if reinvest_div and shares > 0 and prev_d is not None:
            shares += _reinvest_dividend(shares, close, div_yields.get(d), (cur_d - prev_d).days)
        nav.append(NAVPoint(date=d, nav=cash + shares * close))
        prev_d = cur_d
    return _finalize("buy_hold", nav, trades)


def _run_dca(
    quotes, percentiles, boundaries, fee, slip, div_yields, reinvest_div,
    base_amount: Decimal = Decimal("1"),
) -> StrategyResult:
    if not quotes:
        return StrategyResult(name="dca", annualized_return=Decimal(0),
                              max_drawdown=Decimal(0), final_nav=Decimal(1),
                              trade_count=0)

    def _mul(p: Decimal | None) -> Decimal:
        if p is None or boundaries is None:
            return Decimal("1")
        if p < boundaries["extreme_low_upper"]:
            return Decimal("2.0")
        if p < boundaries["low_upper"]:
            return Decimal("2.0")
        if p < boundaries["high_lower"]:
            return Decimal("1.0")
        if p < boundaries["extreme_high_lower"]:
            return Decimal("0.5")
        return Decimal("0.0")

    invested = Decimal(0)
    shares = Decimal(0)
    trades: list[Trade] = []
    nav: list[NAVPoint] = []
    seen_months: set[tuple[int, int]] = set()
    prev_d: date | None = None
    for d, close in quotes:
        cur_d = date.fromisoformat(d)
        if reinvest_div and shares > 0 and prev_d is not None:
            shares += _reinvest_dividend(shares, close, div_yields.get(d), (cur_d - prev_d).days)
        key = (cur_d.year, cur_d.month)
        if key not in seen_months and close > 0:
            p = percentiles.get(d)
            mul = _mul(p)
            this_invest = base_amount * mul
            if this_invest > 0:
                new_shares, _ = _apply_buy_cost(this_invest, close, fee, slip)
                shares += new_shares
                invested += this_invest
                trades.append(Trade(d, "DCA_BUY", close, p,
                                    amount=this_invest, multiplier=mul))
            seen_months.add(key)
        nav.append(NAVPoint(
            date=d,
            nav=(shares * close) / invested if invested > 0 else Decimal(1),
        ))
        prev_d = cur_d
    return _finalize("dca", nav, trades)


def _run_by_temperature(
    quotes, temperatures, fee, slip, div_yields, reinvest_div,
) -> StrategyResult:
    """SRS v1.3.1 B-fix：按温度档位调仓策略。

    规则（与 SRS D1 默认档位对齐；语义"持有"= 持有标的而非现金）：
      温度 ≤ 30  → 100% 满仓
      30 < 温度 < 70 → 100% 满仓（合理区间是基线，应该满仓持有标的）
      70 ≤ 温度 < 90 → 50% 半仓
      温度 ≥ 90 → 0% 清仓

    旧 bug：合理区间返回 "不动"，但起始 shares=0 时永远不会开仓 → 错过全部牛市。
    新设计：合理区间默认满仓；跨过 70 才减仓；跌回 70 以下重新满仓。

    实现：每个交易日检查当日温度，若目标仓位 != 当前仓位，按 close 调仓。
    """
    cash = Decimal(1)
    shares = Decimal(0)
    trades: list[Trade] = []
    nav: list[NAVPoint] = []
    prev_d: date | None = None

    def _target_ratio(temp: Decimal) -> Decimal:
        if temp < Decimal(70):
            return Decimal(1)         # ≤ 30 + 30-70 都满仓
        if temp < Decimal(90):
            return Decimal("0.5")     # 高估半仓
        return Decimal(0)             # 极度高估清仓

    for d, close in quotes:
        if close <= 0:
            continue
        cur_d = date.fromisoformat(d)
        if reinvest_div and shares > 0 and prev_d is not None:
            shares += _reinvest_dividend(shares, close, div_yields.get(d), (cur_d - prev_d).days)
        total = cash + shares * close
        nav.append(NAVPoint(date=d, nav=total))
        prev_d = cur_d
        temp = temperatures.get(d)
        if temp is None or total <= 0:
            continue
        target = _target_ratio(temp)
        target_share_value = total * target
        current_share_value = shares * close
        diff = target_share_value - current_share_value
        if abs(diff) < total * Decimal("0.02"):
            # 差异小于 2% 不调（避免频繁交易）
            continue
        if diff > 0:
            # 加仓：用 cash 买
            buy_cash = min(cash, diff)
            new_shares, _ = _apply_buy_cost(buy_cash, close, fee, slip)
            shares += new_shares
            cash -= buy_cash
            trades.append(Trade(d, "BUY", close, None, amount=buy_cash))
        else:
            # 减仓：卖部分 shares
            sell_shares = min(shares, abs(diff) / close)
            new_cash, _ = _apply_sell_cost(sell_shares, close, fee, slip)
            shares -= sell_shares
            cash += new_cash
            trades.append(Trade(d, "SELL", close, None, amount=new_cash))
    return _finalize("by_temperature", nav, trades)


def _finalize(name: str, nav: list[NAVPoint], trades: list[Trade]) -> StrategyResult:
    final = nav[-1].nav if nav else Decimal(1)
    return StrategyResult(
        name=name,
        annualized_return=_annualized([(n.date, n.nav) for n in nav]),
        max_drawdown=_max_drawdown([(n.date, n.nav) for n in nav]),
        final_nav=final,
        trade_count=len(trades),
        trades=trades,
        nav_curve=nav,
    )


def run_backtest(
    index_code: str,
    quotes: list[tuple[str, Decimal]],
    percentiles: dict[str, Decimal],
    buy_below: Decimal,
    sell_above: Decimal,
    start: str,
    end: str,
    fee_rate: Decimal = Decimal(0),
    slippage_rate: Decimal = Decimal(0),
    reinvest_dividend: bool = False,
    dividend_yields: dict[str, Decimal] | None = None,
    include_dca: bool = True,
    dca_boundaries: dict[str, Decimal] | None = None,
    temperatures: dict[str, Decimal] | None = None,
) -> BacktestResult:
    div_yields = dividend_yields or {}
    in_range = [(d, c) for d, c in quotes if start <= d <= end]
    th = _run_threshold(in_range, percentiles, buy_below, sell_above,
                        fee_rate, slippage_rate, div_yields, reinvest_dividend)
    bh = _run_buy_hold(in_range, fee_rate, slippage_rate, div_yields, reinvest_dividend)
    dca = (
        _run_dca(in_range, percentiles, dca_boundaries, fee_rate, slippage_rate,
                 div_yields, reinvest_dividend)
        if include_dca else None
    )
    by_temp = (
        _run_by_temperature(in_range, temperatures, fee_rate, slippage_rate,
                            div_yields, reinvest_dividend)
        if temperatures else None
    )
    return BacktestResult(
        index_code=index_code,
        start_date=in_range[0][0] if in_range else start,
        end_date=in_range[-1][0] if in_range else end,
        buy_percentile_below=buy_below,
        sell_percentile_above=sell_above,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
        reinvest_dividend=reinvest_dividend,
        threshold=th,
        dca=dca,
        buy_hold=bh,
        by_temperature=by_temp,
    )


def _annualized(nav_curve: list[tuple[str, Decimal]]) -> Decimal:
    if len(nav_curve) < 2:
        return Decimal("0")
    first_d = date.fromisoformat(nav_curve[0][0])
    last_d = date.fromisoformat(nav_curve[-1][0])
    days = (last_d - first_d).days
    if days <= 0:
        return Decimal("0")
    years = Decimal(days) / Decimal("365.25")
    final = nav_curve[-1][1]
    initial = nav_curve[0][1]
    if initial <= 0:
        return Decimal("0")
    ratio = float(final / initial)
    if ratio <= 0:
        return Decimal("-1")
    annualized = ratio ** (1.0 / float(years)) - 1.0
    return Decimal(str(round(annualized, 6)))


def _max_drawdown(nav_curve: list[tuple[str, Decimal]]) -> Decimal:
    if not nav_curve:
        return Decimal("0")
    peak = nav_curve[0][1]
    max_dd = Decimal("0")
    for _, nav in nav_curve:
        if nav > peak:
            peak = nav
        if peak > 0:
            dd = (nav - peak) / peak
            if dd < max_dd:
                max_dd = dd
    return max_dd.quantize(Decimal("0.000001"))
