"""SRS R12 §11.2.4：个股数据源适配器抽象。

与指数适配器（IndexQuote-oriented）分离，避免共用 QuoteRow 引入字段污染。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable


@dataclass(slots=True)
class StockQuoteRow:
    """个股日频行情 + 估值原始字段。任一指标可为 None。"""

    code: str          # 600519.SH / 000001.SZ
    date: str          # YYYY-MM-DD
    close: Decimal
    pe_ttm: Decimal | None = None
    pe: Decimal | None = None         # 静态 PE
    pb: Decimal | None = None
    ps_ttm: Decimal | None = None
    ps: Decimal | None = None
    dividend_yield: Decimal | None = None   # dv_ratio 静态
    dv_ttm: Decimal | None = None
    total_mv: Decimal | None = None         # 万元
    circ_mv: Decimal | None = None
    total_share: Decimal | None = None      # 万股
    source: str = ""


@dataclass(slots=True)
class StockInfo:
    """新加入自选个股时拉取的基础信息。"""

    code: str
    name: str
    industry_raw: str | None              # M6-A：东方财富行业；M6-B 切到申万
    listing_date: str | None              # YYYY-MM-DD
    total_share: Decimal | None = None


class StockDataAdapter(ABC):
    name: str = "abstract"

    @abstractmethod
    def fetch_info(self, code: str) -> StockInfo:
        """新加入自选个股时调用一次，取行业 + 上市日。"""
        ...

    @abstractmethod
    def fetch_quotes(
        self, codes: list[str], start: date, end: date,
    ) -> Iterable[StockQuoteRow]:
        ...

    def health_check(self) -> bool:
        return True
