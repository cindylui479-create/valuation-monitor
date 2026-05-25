from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class BacktestRequest(BaseModel):
    index_code: str = Field(..., min_length=1)
    buy_percentile_below: Decimal = Field(..., ge=0, le=1)
    sell_percentile_above: Decimal = Field(..., ge=0, le=1)
    start_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    window: str = Field(default="10y", pattern=r"^(5y|10y|all)$")
    fee_rate: Decimal = Field(default=Decimal(0), ge=0, le=Decimal("0.05"))
    slippage_rate: Decimal = Field(default=Decimal(0), ge=0, le=Decimal("0.05"))
    reinvest_dividend: bool = Field(default=False)
    include_dca: bool = Field(default=True)

    @model_validator(mode="after")
    def check_thresholds(self) -> "BacktestRequest":
        if self.buy_percentile_below >= self.sell_percentile_above:
            raise ValueError("buy_percentile_below must be < sell_percentile_above")
        return self


class TradeDTO(BaseModel):
    date: str
    action: str
    price: str
    pe_percentile: str | None
    amount: str
    multiplier: str | None = None


class NAVPointDTO(BaseModel):
    date: str
    nav: str


class StrategyResultDTO(BaseModel):
    name: str
    annualized_return: str
    max_drawdown: str
    final_nav: str
    trade_count: int
    trades: list[TradeDTO]
    nav_curve: list[NAVPointDTO]


class BacktestResponse(BaseModel):
    index_code: str
    index_name: str
    start_date: str
    end_date: str
    buy_percentile_below: str
    sell_percentile_above: str
    fee_rate: str
    slippage_rate: str
    reinvest_dividend: bool

    threshold: StrategyResultDTO
    dca: StrategyResultDTO | None
    buy_hold: StrategyResultDTO
    by_temperature: StrategyResultDTO | None = None
