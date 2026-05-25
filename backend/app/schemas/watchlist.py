from pydantic import BaseModel, Field


class WatchlistItem(BaseModel):
    """自选指数项，含估值实况快照（参考 §11.2.6 个股列表 UI）。"""

    id: int
    index_code: str
    index_name: str
    market: str | None = None             # A / HK / US
    category: str | None = None           # 宽基 / 行业 / 主题
    industry_raw: str | None = None
    tag: str | None
    added_at: str
    # 估值实况（按 pe_source 取，沿用 latest_with_fallback）
    temperature: str | None = None
    tier: str | None = None
    pe_ttm: str | None = None
    pb: str | None = None
    dividend_yield: str | None = None
    valuation_source: str | None = None   # 'lg' / 'csi' / null
    temperature_source: str | None = None # pe_10y / pe_all / price_10y / price_all / null
    actual_history_years: float | None = None
    data_window_note: str | None = None


class WatchlistCreate(BaseModel):
    index_code: str = Field(..., min_length=1)
    tag: str | None = Field(default=None, max_length=32)
