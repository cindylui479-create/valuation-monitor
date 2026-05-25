from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable


@dataclass(slots=True)
class QuoteRow:
    """适配器输出的标准行；任一指标可为 None。"""

    index_code: str
    date: str  # YYYY-MM-DD
    close: Decimal
    pe_ttm: Decimal | None = None
    pb: Decimal | None = None
    dividend_yield: Decimal | None = None
    roe: Decimal | None = None
    earnings_growth_3y: Decimal | None = None
    ma50: Decimal | None = None
    ma200: Decimal | None = None
    northbound_60d_pct: Decimal | None = None
    source: str = ""


class DataSourceAdapter(ABC):
    name: str = "abstract"
    supported_markets: tuple[str, ...] = ()

    @abstractmethod
    def fetch_quotes(
        self,
        index_codes: list[str],
        start: date,
        end: date,
    ) -> Iterable[QuoteRow]:
        ...

    @abstractmethod
    def fetch_calendar(self, market: str, year: int) -> list[tuple[str, bool]]:
        ...

    def health_check(self) -> bool:
        return True
