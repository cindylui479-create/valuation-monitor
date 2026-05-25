from __future__ import annotations

from functools import lru_cache

from app.adapters.akshare_adapter import AkshareAdapter
from app.adapters.base import DataSourceAdapter
from app.adapters.tushare_adapter import TushareAdapter
from app.adapters.yfinance_adapter import YfinanceAdapter
from app.utils.exceptions import AdapterNotFound


# 按 index_code 覆盖默认市场主源。这里的 code 优先匹配；命中后 fetch_quotes 走
# 指定 adapter，失败再 fallback 到 _fallback_by_market[market] 中其他源。
# 用途：上证综指/深证成指/创业板指 → Tushare（10y 完整 PE 历史），优于 sina 仅 close。
_PER_INDEX_PRIMARY: dict[str, str] = {
    "000001.SH": "tushare",   # 上证综指
    "399001.SZ": "tushare",   # 深证成指
    "399006.SZ": "tushare",   # 创业板指
}


class AdapterRegistry:
    """按市场返回首选 + 回退顺序的适配器列表。

    - A 股 → akshare（lg+sina）主，tushare 作为部分指数的指定主源（per-index）
    - 港股 → yfinance
    - 美股 → yfinance
    """

    def __init__(self) -> None:
        self._by_name: dict[str, DataSourceAdapter] = {}
        self._fallback_by_market: dict[str, list[DataSourceAdapter]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        ak = AkshareAdapter()
        yf = YfinanceAdapter()
        ts = TushareAdapter()
        self._by_name[ak.name] = ak
        self._by_name[yf.name] = yf
        self._by_name[ts.name] = ts
        # A 股回退顺序：akshare 优先（覆盖 lg + sina），tushare 兜底
        self._fallback_by_market["A"] = [ak, ts]
        self._fallback_by_market["HK"] = [yf]
        self._fallback_by_market["US"] = [yf]

    def get(self, name: str) -> DataSourceAdapter:
        adp = self._by_name.get(name)
        if adp is None:
            raise AdapterNotFound(name)
        return adp

    def fallbacks(self, market: str) -> list[DataSourceAdapter]:
        return list(self._fallback_by_market.get(market, []))

    def fallbacks_for_index(self, market: str, index_code: str) -> list[DataSourceAdapter]:
        """对单个 index 返回 adapter 顺序。如果该 code 在 _PER_INDEX_PRIMARY 中，
        指定 adapter 放在最前；其余按市场默认顺序排在后面（作为 fallback）。"""
        market_list = self.fallbacks(market)
        primary_name = _PER_INDEX_PRIMARY.get(index_code)
        if primary_name is None:
            return market_list
        primary = self._by_name.get(primary_name)
        if primary is None:
            return market_list
        # 把 primary 提到首位（去重）
        rest = [a for a in market_list if a.name != primary.name]
        return [primary, *rest]

    def primary(self, market: str) -> DataSourceAdapter:
        adapters = self.fallbacks(market)
        if not adapters:
            raise AdapterNotFound(f"no adapter for market {market}")
        return adapters[0]


@lru_cache
def get_registry() -> AdapterRegistry:
    return AdapterRegistry()
