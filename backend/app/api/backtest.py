from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import db_session
from app.errors import BusinessRuleViolation, NotFound
from app.repositories import index_repo, quote_repo, valuation_repo
from app.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    NAVPointDTO,
    StrategyResultDTO,
    TradeDTO,
)
from app.services.backtest_runner import StrategyResult, run_backtest
from app.services.boundaries_service import boundaries_for
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


def _strategy_dto(s: StrategyResult) -> StrategyResultDTO:
    return StrategyResultDTO(
        name=s.name,
        annualized_return=decimal_to_str(s.annualized_return) or "0",
        max_drawdown=decimal_to_str(s.max_drawdown) or "0",
        final_nav=decimal_to_str(s.final_nav) or "1",
        trade_count=s.trade_count,
        trades=[
            TradeDTO(
                date=t.date,
                action=t.action,
                price=decimal_to_str(t.price) or "0",
                pe_percentile=decimal_to_str(t.pe_percentile),
                amount=decimal_to_str(t.amount) or "0",
                multiplier=decimal_to_str(t.multiplier) if t.multiplier is not None else None,
            )
            for t in s.trades
        ],
        nav_curve=[
            NAVPointDTO(date=p.date, nav=decimal_to_str(p.nav) or "1")
            for p in s.nav_curve
        ],
    )


@router.post("/backtest/run", response_model=BacktestResponse)
def run(body: BacktestRequest, session: Session = Depends(db_session)) -> BacktestResponse:
    idx = index_repo.get_by_code(session, body.index_code)
    if idx is None:
        raise NotFound("index not found", code=body.index_code)

    quotes = quote_repo.list_recent(session, idx.id, limit=20_000)
    quotes.sort(key=lambda q: q.date)
    if not quotes:
        raise BusinessRuleViolation("无历史行情数据", code=body.index_code)
    quote_pairs = [(q.date, q.close) for q in quotes]

    val_rows = valuation_repo.series(session, idx.id, window=body.window)
    percentiles = {v.date: v.pe_percentile for v in val_rows if v.pe_percentile is not None}
    if not percentiles:
        raise BusinessRuleViolation(
            "该指数无 PE 分位历史数据，不能回测（港美股暂未累积满 1 年）",
            code=body.index_code,
        )

    div_yields = {q.date: q.dividend_yield for q in quotes if q.dividend_yield is not None}

    available_dates = [d for d, _ in quote_pairs]
    start = body.start_date or available_dates[0]
    end = body.end_date or available_dates[-1]
    if start > end:
        raise BusinessRuleViolation("start_date must be <= end_date", start=start, end=end)

    b = boundaries_for(session, idx.id)
    dca_boundaries = {
        "extreme_low_upper": b.extreme_low_upper,
        "low_upper": b.low_upper,
        "high_lower": b.high_lower,
        "extreme_high_lower": b.extreme_high_lower,
    }

    result = run_backtest(
        index_code=body.index_code,
        quotes=quote_pairs,
        percentiles=percentiles,
        buy_below=body.buy_percentile_below,
        sell_above=body.sell_percentile_above,
        start=start,
        end=end,
        fee_rate=body.fee_rate,
        slippage_rate=body.slippage_rate,
        reinvest_dividend=body.reinvest_dividend,
        dividend_yields=div_yields,
        include_dca=body.include_dca,
        dca_boundaries=dca_boundaries,
    )

    return BacktestResponse(
        index_code=idx.code,
        index_name=idx.name,
        start_date=result.start_date,
        end_date=result.end_date,
        buy_percentile_below=decimal_to_str(result.buy_percentile_below) or "0",
        sell_percentile_above=decimal_to_str(result.sell_percentile_above) or "0",
        fee_rate=decimal_to_str(result.fee_rate) or "0",
        slippage_rate=decimal_to_str(result.slippage_rate) or "0",
        reinvest_dividend=result.reinvest_dividend,
        threshold=_strategy_dto(result.threshold),
        dca=_strategy_dto(result.dca) if result.dca else None,
        buy_hold=_strategy_dto(result.buy_hold),
    )
