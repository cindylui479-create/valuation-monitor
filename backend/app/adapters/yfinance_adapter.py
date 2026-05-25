"""yfinance 适配器（港股 + 美股）。

历史 OHLC：`Ticker.history(period='max')` —— 完整历史，10+ 年
当日估值快照：`Ticker.info.trailingPE / priceToBook / dividendYield` —— 仅当日值

注意 SRS 附录 B R7：港美股 PE/PB **仅当日快照入库**，不参与历史分位计算；
分位与温度仅有 A 股锚定 10 年滚动窗口（SRS D1）。
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from app.adapters.base import DataSourceAdapter, QuoteRow
from app.utils.decimal_utils import to_decimal
from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("adapter.yfinance")


# yfinance 中 `^` 开头的指数 ticker 不返回 trailingPE / priceToBook / dividendYield；
# 改用一只跟踪该指数的 ETF 取「估值代理快照」。仅取 Ticker.info，价格仍走指数本身。
_PE_INFO_PROXY: dict[str, str] = {
    "^HSI": "EWH",     # iShares MSCI Hong Kong，PE 跟恒生指数高度相关
    "^HSCE": "FXI",    # iShares HSCEI（中国大型股 ETF），跟踪恒生国企
}


def _import_yf():
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError as e:
        raise FetchFailure(f"yfinance not installed: {e}") from e
    return yf


class YfinanceAdapter(DataSourceAdapter):
    name = "yfinance"
    supported_markets = ("HK", "US")

    def fetch_quotes(
        self,
        index_codes: list[str],
        start: date,
        end: date,
    ) -> Iterable[QuoteRow]:
        yf = _import_yf()
        start_s = start.isoformat()
        end_s = end.isoformat()

        for code in index_codes:
            try:
                yield from self._fetch_one(yf, code, start_s, end_s)
            except Exception as e:
                log.error("yfinance.fetch_failed", code=code, error=str(e))
                raise FetchFailure(f"yfinance fetch failed for {code}: {e}") from e

    def _fetch_one(self, yf, code: str, start_s: str, end_s: str) -> Iterable[QuoteRow]:
        t = yf.Ticker(code)
        hist = t.history(period="max", auto_adjust=False)
        if hist is None or hist.empty:
            log.warning("yfinance.no_history", code=code)
            return

        # 估值快照：指数 `^XXX` 在 yfinance 不带 PE，转用代理 ETF 的 Ticker.info
        proxy_code = _PE_INFO_PROXY.get(code, code)
        proxy_t = yf.Ticker(proxy_code) if proxy_code != code else t
        info = self._safe_info(proxy_t)
        snap_pe = to_decimal(info.get("trailingPE"))
        snap_pb = to_decimal(info.get("priceToBook"))
        snap_dy_pct = info.get("dividendYield")  # yfinance 给百分数（如 0.42 表示 0.42%）
        snap_dy = (
            Decimal(str(snap_dy_pct)) / Decimal(100) if snap_dy_pct is not None else None
        )
        if proxy_code != code:
            log.info("yfinance.pe_proxy", code=code, proxy=proxy_code, pe=str(snap_pe))

        hist = hist.reset_index()
        hist["date"] = hist["Date"].astype(str).str.slice(0, 10)
        mask = (hist["date"] >= start_s) & (hist["date"] <= end_s)
        df = hist.loc[mask].copy()

        last_date_str = df["date"].iloc[-1] if len(df) else None

        for _, row in df.iterrows():
            d = row["date"]
            # 仅最新一行附加快照；其他历史日缺失 → None（不进入分位）
            pe = snap_pe if d == last_date_str else None
            pb = snap_pb if d == last_date_str else None
            dy = snap_dy if d == last_date_str else None
            yield QuoteRow(
                index_code=code,
                date=d,
                close=to_decimal(row.get("Close")) or Decimal(0),
                pe_ttm=pe,
                pb=pb,
                dividend_yield=dy,
                source=self.name,
            )

    @staticmethod
    def _safe_info(t) -> dict:  # noqa: ANN001
        try:
            return dict(t.info or {})
        except Exception as e:
            log.warning("yfinance.info_failed", error=str(e))
            return {}

    def fetch_calendar(self, market: str, year: int) -> list[tuple[str, bool]]:
        # yfinance 不提供干净的交易日历；占位返回空（系统兜底用周一~周五）
        return []

    def health_check(self) -> bool:
        try:
            yf = _import_yf()
            h = yf.Ticker("SPY").history(period="5d")
            return len(h) > 0
        except Exception:
            return False
