from pydantic import BaseModel


class FundDTO(BaseModel):
    code: str
    name: str
    type: str
    fee_rate: str | None
    tracking_error_note: str | None


class IndexDTO(BaseModel):
    code: str
    name: str
    market: str
    category: str
    industry_raw: str | None
    data_source: str
    history_start_date: str
    enabled: bool
    funds: list[FundDTO] = []
