from pydantic import BaseModel


class ValuationPoint(BaseModel):
    date: str
    pe_ttm: str | None
    pe_percentile: str | None
    pb_percentile: str | None
    dy_percentile: str | None
    temperature: str | None
    tier: str | None


class ValuationSeriesResponse(BaseModel):
    code: str
    window: str
    series: list[ValuationPoint]
