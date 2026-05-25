"""Tushare Pro 适配器（A 股 — 主要服务于"上证综指/深证成指/创业板指"等综合指数）。

接口（需 2000 积分）：
- `pro.index_daily(ts_code, start_date, end_date)`：OHLC + 涨跌
- `pro.index_dailybasic(ts_code, start_date, end_date)`：pe / pe_ttm / pb / total_mv

字段映射：close → close；pe_ttm → pe_ttm；pb → pb。
股息率 dv_ttm 不在 index_dailybasic 中（成分股聚合实现成本高，留作未来工作）。

需环境变量 `TUSHARE_TOKEN`；未设置则 health_check 返回 False，fetch 抛 FetchFailure。
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from app.adapters.base import DataSourceAdapter, QuoteRow
from app.config import get_settings
from app.utils.decimal_utils import to_decimal
from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("adapter.tushare")


def _import_ts():
    try:
        import tushare as ts  # noqa: PLC0415
    except ImportError as e:
        raise FetchFailure(f"tushare not installed: {e}") from e
    return ts


def _get_pro():
    token = (get_settings().tushare_token or "").strip()
    if not token:
        raise FetchFailure("TUSHARE_TOKEN not set")
    ts = _import_ts()
    ts.set_token(token)
    # Tushare 默认 timeout 30s 在弱网/拉 10y 时不够；放宽到 180s
    from app.utils.tushare_meter import wrap_pro
    try:
        return wrap_pro(ts.pro_api(timeout=180))
    except TypeError:
        return wrap_pro(ts.pro_api())


class TushareAdapter(DataSourceAdapter):
    name = "tushare"
    supported_markets = ("A",)

    def fetch_quotes(
        self,
        index_codes: list[str],
        start: date,
        end: date,
    ) -> Iterable[QuoteRow]:
        pro = _get_pro()
        start_s = start.strftime("%Y%m%d")
        end_s = end.strftime("%Y%m%d")

        for code in index_codes:
            try:
                yield from self._fetch_one(pro, code, start_s, end_s)
            except FetchFailure:
                raise
            except Exception as e:
                log.error("tushare.fetch_failed", code=code, error=str(e))
                raise FetchFailure(f"tushare fetch failed for {code}: {e}") from e

    def _fetch_one(
        self,
        pro,  # noqa: ANN001
        code: str,
        start_s: str,
        end_s: str,
    ) -> Iterable[QuoteRow]:
        daily = pro.index_daily(ts_code=code, start_date=start_s, end_date=end_s)
        basic = pro.index_dailybasic(ts_code=code, start_date=start_s, end_date=end_s)
        if daily is None or daily.empty:
            # 抛 FetchFailure 触发 fallback（akshare sina 路径），而不是静默返回空
            raise FetchFailure(f"tushare returned empty for {code}")
        # daily.trade_date / basic.trade_date 都是 YYYYMMDD（字符串）；统一转 YYYY-MM-DD
        basic_by_date: dict[str, dict] = {}
        if basic is not None and not basic.empty:
            for _, row in basic.iterrows():
                d = self._normalize_date(row["trade_date"])
                basic_by_date[d] = row

        for _, row in daily.iterrows():
            d = self._normalize_date(row["trade_date"])
            b = basic_by_date.get(d)
            yield QuoteRow(
                index_code=code,
                date=d,
                close=to_decimal(row.get("close")) or Decimal(0),
                pe_ttm=to_decimal(b.get("pe_ttm")) if b is not None else None,
                pb=to_decimal(b.get("pb")) if b is not None else None,
                dividend_yield=None,                  # index_dailybasic 不提供
                source=self.name,
            )

    @staticmethod
    def _normalize_date(s: str | int) -> str:
        """YYYYMMDD → YYYY-MM-DD。"""
        s = str(s)
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"

    def fetch_calendar(self, market: str, year: int) -> list[tuple[str, bool]]:
        if market != "A":
            return []
        try:
            pro = _get_pro()
            df = pro.trade_cal(exchange="SSE", start_date=f"{year}0101", end_date=f"{year}1231")
            return [
                (f"{str(r['cal_date'])[:4]}-{str(r['cal_date'])[4:6]}-{str(r['cal_date'])[6:8]}",
                 bool(r["is_open"]))
                for _, r in df.iterrows()
            ]
        except Exception:
            return []

    def health_check(self) -> bool:
        try:
            pro = _get_pro()
            df = pro.index_daily(ts_code="000300.SH", start_date="20240101", end_date="20240105")
            return len(df) > 0
        except Exception:
            return False
