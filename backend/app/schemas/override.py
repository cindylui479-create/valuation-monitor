from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class Boundaries(BaseModel):
    extreme_low_upper: Decimal | None = Field(default=None, ge=0, le=1)
    low_upper: Decimal | None = Field(default=None, ge=0, le=1)
    high_lower: Decimal | None = Field(default=None, ge=0, le=1)
    extreme_high_lower: Decimal | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def check_ordering(self) -> "Boundaries":
        # 用默认值补齐用于排序校验
        vals = [
            self.extreme_low_upper if self.extreme_low_upper is not None else Decimal("0.10"),
            self.low_upper if self.low_upper is not None else Decimal("0.30"),
            self.high_lower if self.high_lower is not None else Decimal("0.70"),
            self.extreme_high_lower if self.extreme_high_lower is not None else Decimal("0.90"),
        ]
        if not all(vals[i] < vals[i + 1] for i in range(3)):
            raise ValueError(
                "boundaries must satisfy: extreme_low_upper < low_upper < high_lower < extreme_high_lower"
            )
        return self


class ThresholdOverrideResponse(BaseModel):
    index_code: str
    boundaries: Boundaries
    is_default: bool  # True 表示该指数没有覆盖记录，返回的是 DEFAULT_BOUNDARIES
    updated_at: str | None
