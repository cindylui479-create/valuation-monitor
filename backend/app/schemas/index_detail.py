from pydantic import BaseModel

from app.schemas.index import FundDTO


class QuotePoint(BaseModel):
    date: str
    close: str
    pe_ttm: str | None
    pb: str | None
    dividend_yield: str | None


class ValuationPoint(BaseModel):
    date: str
    pe_percentile: str | None
    pb_percentile: str | None
    temperature: str | None
    tier: str | None
    temperature_source: str | None = None    # pe_10y / pe_all / price_10y / price_all / null


class SignalPoint(BaseModel):
    date: str
    direction: str
    tier: str
    temperature: str


class IndexDetailResponse(BaseModel):
    code: str
    name: str
    market: str
    currency: str
    category: str
    industry_raw: str | None
    history_start_date: str            # YAML 理论
    actual_history_years: float        # DB 实际（R3）
    data_window_note: str | None
    enabled: bool
    funds: list[FundDTO]
    latest_valuation: ValuationPoint | None
    latest_signal: SignalPoint | None
    signal_history: list[SignalPoint]   # 该指数所有信号（按日期倒序）
    quotes: list[QuotePoint]           # 近 N 天
    valuation_series: list[ValuationPoint]  # 近 N 天对应分位
