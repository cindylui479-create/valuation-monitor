from pydantic import BaseModel


class OverviewIndex(BaseModel):
    code: str
    name: str
    category: str
    tier: str | None
    temperature: str | None  # Decimal as string
    pe_ttm: str | None
    pe_percentile_10y: str | None
    pb_percentile_10y: str | None
    dividend_yield: str | None
    ma50_deviation: str | None
    ma200_deviation: str | None
    data_window_note: str | None
    temperature_source: str | None = None   # pe_10y / pe_all / price_10y / price_all
    funds_count: int


class OverviewMarket(BaseModel):
    market: str
    currency: str
    indices: list[OverviewIndex]


class OverviewResponse(BaseModel):
    as_of: str | None
    markets: list[OverviewMarket]
