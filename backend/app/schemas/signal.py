from pydantic import BaseModel


class SignalDTO(BaseModel):
    id: int
    index_code: str
    index_name: str
    market: str
    date: str
    direction: str               # STRONG_BUY / BUY / SELL / STRONG_SELL
    tier: str
    temperature: str             # Decimal as string
    generated_at: str


class SignalListResponse(BaseModel):
    items: list[SignalDTO]
    total: int
