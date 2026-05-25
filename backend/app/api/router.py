from fastapi import APIRouter

from app.api import (
    backtest,
    data_quality,
    dca,
    exports,
    funds,
    health,
    holdings,
    opportunities,
    rebalance,
    search,
    temperature_effectiveness,
    tier_transitions,
    tushare_usage,
    index_detail,
    indices,
    overrides,
    overview,
    pipeline_runs,
    preferences,
    signals,
    stocks,
    valuation,
    watchlist,
)

api_router = APIRouter()
api_router.include_router(overview.router, tags=["overview"])
api_router.include_router(indices.router, tags=["indices"])
api_router.include_router(index_detail.router, tags=["indices"])
api_router.include_router(valuation.router, tags=["valuation"])
api_router.include_router(watchlist.router, tags=["watchlist"])
api_router.include_router(signals.router, tags=["signals"])
api_router.include_router(dca.router, tags=["dca"])
api_router.include_router(overrides.router, tags=["thresholds"])
api_router.include_router(backtest.router, tags=["backtest"])
api_router.include_router(exports.router, tags=["exports"])
api_router.include_router(preferences.router, tags=["preferences"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(pipeline_runs.router, tags=["health"])
api_router.include_router(data_quality.router, tags=["data-quality"])
api_router.include_router(stocks.router, tags=["stocks"])
api_router.include_router(funds.router, tags=["funds"])
api_router.include_router(holdings.router, tags=["holdings"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(tier_transitions.router, tags=["transitions"])
api_router.include_router(opportunities.router, tags=["opportunities"])
api_router.include_router(temperature_effectiveness.router, tags=["effectiveness"])
api_router.include_router(tushare_usage.router, tags=["tushare"])
api_router.include_router(rebalance.router, tags=["holdings"])
