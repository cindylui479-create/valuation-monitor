"""SRS R12 §11.2.4：Tushare 个股主源适配器（A 股）。

接口：
- `pro.stock_basic`：取股票基础信息（行业 / 上市日 / 总股本）
- `pro.daily_basic(ts_code, start_date, end_date)`：日频估值（pe/pe_ttm/pb/ps/dv_ttm/total_mv）

需环境变量 `TUSHARE_TOKEN`；未设置则抛 FetchFailure。
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from app.adapters.stock_base import StockDataAdapter, StockInfo, StockQuoteRow
from app.config import get_settings
from app.utils.decimal_utils import to_decimal
from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("adapter.stock_tushare")


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
    from app.utils.tushare_meter import wrap_pro
    try:
        return wrap_pro(ts.pro_api(timeout=180))
    except TypeError:
        return wrap_pro(ts.pro_api())


def _normalize_ts_code(code: str) -> str:
    """600519.SH / 000001.SZ → Tushare ts_code 格式（同形式即可）。"""
    code = code.strip().upper()
    if "." in code:
        return code
    # 仅 6 位数字时按交易所推断
    if code.startswith(("60", "68", "90")):
        return f"{code}.SH"
    if code.startswith(("00", "30", "20")):
        return f"{code}.SZ"
    if code.startswith(("4", "8")):
        return f"{code}.BJ"
    raise FetchFailure(f"无法识别股票代码归属交易所: {code}")


class StockTushareAdapter(StockDataAdapter):
    name = "tushare"

    def fetch_info(self, code: str) -> StockInfo:
        pro = _get_pro()
        ts_code = _normalize_ts_code(code)
        # stock_basic 字段：ts_code, symbol, name, area, industry, fullname, market, list_date
        try:
            df = pro.stock_basic(
                ts_code=ts_code,
                fields="ts_code,name,industry,market,list_date",
            )
        except Exception as e:
            raise FetchFailure(f"tushare stock_basic 拉取失败 {ts_code}: {e}") from e
        if df is None or df.empty:
            raise FetchFailure(f"tushare 未找到股票: {ts_code}")
        row = df.iloc[0]
        list_date = str(row["list_date"]) if row.get("list_date") else None
        if list_date and len(list_date) == 8:
            list_date = f"{list_date[:4]}-{list_date[4:6]}-{list_date[6:8]}"
        return StockInfo(
            code=ts_code,
            name=str(row["name"]),
            industry_raw=str(row["industry"]) if row.get("industry") else None,
            listing_date=list_date,
            total_share=None,
        )

    def fetch_quotes(
        self, codes: list[str], start: date, end: date,
    ) -> Iterable[StockQuoteRow]:
        pro = _get_pro()
        start_s = start.strftime("%Y%m%d")
        end_s = end.strftime("%Y%m%d")
        for raw_code in codes:
            ts_code = _normalize_ts_code(raw_code)
            try:
                df = pro.daily_basic(
                    ts_code=ts_code,
                    start_date=start_s, end_date=end_s,
                    fields="trade_date,close,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_mv,circ_mv,total_share",
                )
            except Exception as e:
                raise FetchFailure(f"tushare daily_basic {ts_code}: {e}") from e
            if df is None or df.empty:
                log.warning("stock_tushare.empty", code=ts_code, start=start_s, end=end_s)
                continue
            df = df.sort_values("trade_date")
            for _, r in df.iterrows():
                d = str(r["trade_date"])
                date_iso = f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else d
                yield StockQuoteRow(
                    code=ts_code,
                    date=date_iso,
                    close=to_decimal(r["close"]),
                    pe=to_decimal(r.get("pe")),
                    pe_ttm=to_decimal(r.get("pe_ttm")),
                    pb=to_decimal(r.get("pb")),
                    ps=to_decimal(r.get("ps")),
                    ps_ttm=to_decimal(r.get("ps_ttm")),
                    dividend_yield=to_decimal(r.get("dv_ratio")),
                    dv_ttm=to_decimal(r.get("dv_ttm")),
                    total_mv=to_decimal(r.get("total_mv")),
                    circ_mv=to_decimal(r.get("circ_mv")),
                    total_share=to_decimal(r.get("total_share")),
                    source=self.name,
                )

    def health_check(self) -> bool:
        try:
            _get_pro()
            return True
        except Exception:
            return False
