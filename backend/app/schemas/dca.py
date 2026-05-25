from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Frequency = Literal["WEEKLY", "BIWEEKLY", "MONTHLY"]
ExecStatus = Literal["PENDING", "DONE", "SKIPPED"]


class DCAPlanCreate(BaseModel):
    index_code: str = Field(..., min_length=1)
    fund_code: str | None = None
    amount: Decimal = Field(..., gt=0)
    frequency: Frequency
    day_of_period: int = Field(..., ge=1, le=28)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    enabled: bool = True

    @model_validator(mode="after")
    def check_day(self) -> "DCAPlanCreate":
        if self.frequency in {"WEEKLY", "BIWEEKLY"} and not (1 <= self.day_of_period <= 7):
            raise ValueError("day_of_period for WEEKLY/BIWEEKLY must be in 1..7 (Mon..Sun)")
        return self


class DCAPlanUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    frequency: Frequency | None = None
    day_of_period: int | None = Field(default=None, ge=1, le=28)
    enabled: bool | None = None
    fund_code: str | None = None


class DCAPlanDTO(BaseModel):
    id: int
    index_code: str
    index_name: str
    fund_code: str | None
    fund_name: str | None
    amount: str
    frequency: str
    day_of_period: int
    start_date: str
    enabled: bool
    created_at: str
    updated_at: str


class DCAExecutionDTO(BaseModel):
    id: int
    plan_id: int
    index_code: str
    index_name: str
    scheduled_date: str
    actual_date: str
    base_amount: str
    adjusted_amount: str
    multiplier: str
    tier_at_decision: str
    temperature: str
    status: str
    generated_at: str
    marked_at: str | None


class UpcomingReminderResponse(BaseModel):
    items: list[DCAExecutionDTO]


class DCAPlanStatsDTO(BaseModel):
    plan_id: int
    index_code: str
    index_name: str
    done_count: int
    skipped_count: int
    pending_count: int
    done_total_amount: str
    skipped_total_amount: str
    base_total_if_no_adjustment: str
    skip_ratio: str
    average_multiplier: str


class DCAStatsResponse(BaseModel):
    plans: list[DCAPlanStatsDTO]
    total_done_amount: str
    total_skipped_amount: str
