"""SRS R12 §11.3.3 M7-B：场外主动基金 NAV 适配器（akshare 主源）。

接口：
- `fund_individual_basic_info_xq(symbol)`：基金基本信息（成立日、基金经理、基金类型）
- `fund_open_fund_info_em(symbol, indicator="单位净值走势")`：日频净值 1842 行（如 005827）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from app.utils.decimal_utils import to_decimal
from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("adapter.fund_akshare")


@dataclass(slots=True)
class FundInfo:
    code: str
    name: str
    setup_date: str | None        # YYYY-MM-DD
    fund_type_raw: str | None     # 'ETF' / '混合型-偏股' / '股票型' / '债券型' / 'QDII' 等
    fund_manager: str | None
    is_active: bool               # True = 主动基金；False = ETF / 指数型


@dataclass(slots=True)
class NAVPoint:
    code: str
    date: str
    nav: Decimal
    accumulated_nav: Decimal | None = None


_ACTIVE_TYPES = (
    "混合型", "股票型", "债券型", "QDII", "灵活配置", "偏股", "偏债",
)


def _is_active_fund(type_raw: str | None) -> bool:
    if not type_raw:
        return False
    return any(t in type_raw for t in _ACTIVE_TYPES) and ("指数" not in type_raw and "ETF" not in type_raw.upper())


class FundAkshareAdapter:
    name = "akshare_fund"

    def fetch_info(self, code: str) -> FundInfo:
        try:
            import akshare as ak
        except ImportError as e:
            raise FetchFailure(f"akshare not installed: {e}") from e

        try:
            df = ak.fund_individual_basic_info_xq(symbol=code)
        except Exception as e:
            raise FetchFailure(f"akshare fund_individual_basic_info_xq {code}: {e}") from e
        if df is None or df.empty:
            raise FetchFailure(f"未找到基金 {code}")

        # df 结构：item / value 两列
        kv = dict(zip(df["item"], df["value"]))
        name = kv.get("基金名称") or kv.get("基金全称") or code
        setup_raw = kv.get("成立时间")
        setup_date = None
        if setup_raw:
            s = str(setup_raw).strip()
            # akshare 返回的可能是 "2018-09-05" 已 ISO 格式
            if len(s) == 10 and s[4] == "-":
                setup_date = s
        fund_type_raw = kv.get("基金类型")
        fund_manager = kv.get("基金经理")
        type_raw_str = str(fund_type_raw) if fund_type_raw else None
        return FundInfo(
            code=code, name=str(name),
            setup_date=setup_date,
            fund_type_raw=type_raw_str,
            fund_manager=str(fund_manager) if fund_manager else None,
            is_active=_is_active_fund(type_raw_str),
        )

    def fetch_nav_history(self, code: str) -> Iterable[NAVPoint]:
        try:
            import akshare as ak
        except ImportError as e:
            raise FetchFailure(f"akshare not installed: {e}") from e

        try:
            df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        except Exception as e:
            raise FetchFailure(f"akshare fund_open_fund_info_em {code}: {e}") from e
        if df is None or df.empty:
            raise FetchFailure(f"基金 {code} 无 NAV 历史")
        date_col = "净值日期"
        nav_col = "单位净值"
        for _, r in df.iterrows():
            d_raw = str(r[date_col])
            # 接受 "YYYY-MM-DD" 或 datetime
            if "-" in d_raw[:10]:
                date_iso = d_raw[:10]
            else:
                continue
            yield NAVPoint(
                code=code,
                date=date_iso,
                nav=to_decimal(r[nav_col]),
                accumulated_nav=None,
            )

    def health_check(self) -> bool:
        try:
            import akshare  # noqa: F401
            return True
        except ImportError:
            return False
