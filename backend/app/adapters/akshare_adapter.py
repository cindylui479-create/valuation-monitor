"""AkShare 适配器（A 股 + 港股）。

A 股估值历史接口：
- `stock_index_pe_lg(symbol)`：日期、指数点位、PE-TTM（5000+ 行历史）
- `stock_index_pb_lg(symbol)`：日期、指数点位、PB（5000+ 行历史）
- `stock_zh_index_value_csindex(symbol)`：中证指数公司，仅给最近 20 个交易日的**股息率**
  快照（SRS 附录 B R2）；按日期 left-join 进 QuoteRow，每日批处理逐步累积历史

交易日历：`tool_trade_date_hist_sina`
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from app.adapters.base import DataSourceAdapter, QuoteRow
from app.utils.decimal_utils import to_decimal
from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("adapter.akshare")


# 内置代码 → 乐咕乐股需要的中文名称
# 支持的指数清单参见 ak.stock_index_pe_lg 的 docstring
_LG_NAME = {
    # 宽基（M1）
    "000300.SH": "沪深300",
    "000905.SH": "中证500",
    "000906.SH": "中证800",
    "000852.SH": "中证1000",
    "000016.SH": "上证50",
    # M2 新增
    "000903.SH": "中证100",
    "399673.SZ": "创业板50",
    "000015.SH": "上证红利",
}

# 中证指数公司 6 位代码（用于 csindex_value 估值快照：PE / 股息率）。
# 仅中证编制的指数受支持；非中证编制（深证编制）返回 None 跳过。
_CSINDEX_CODE = {
    "000300.SH": "000300",
    "000905.SH": "000905",
    "000906.SH": "000906",
    "000852.SH": "000852",
    "000016.SH": "000016",
    "000903.SH": "000903",
    "000015.SH": "000015",
    # M3 末扩充
    "000932.SH": "000932",    # 中证消费
    "H30269.CSI": "H30269",   # 中证红利低波动指数
    "000001.SH": "000001",    # 上证综指
    "000688.SH": "000688",    # 科创板 50
}

# 新浪指数日行情代码（lg 池外指数；走 stock_zh_index_daily 拿 close）
# 注意 sina format："sh000001" / "sz399001" / "sh512890"（ETF 价格代理也走 sh/sz）
_SINA_CODE = {
    "000932.SH": "sh000932",    # 中证消费
    "H30269.CSI": "sh512890",   # 中证红利低波 → 跟踪 ETF 华泰柏瑞 512890 作价格代理
    "000001.SH": "sh000001",    # 上证综指
    "399001.SZ": "sz399001",    # 深证成指（csindex 无）
    "399006.SZ": "sz399006",    # 创业板指（csindex 无）
    "000688.SH": "sh000688",    # 科创板 50
}


def _import_akshare():
    try:
        import akshare as ak  # noqa: PLC0415
    except ImportError as e:
        raise FetchFailure(f"akshare not installed: {e}") from e
    return ak


class AkshareAdapter(DataSourceAdapter):
    name = "akshare"
    supported_markets = ("A", "HK")

    def fetch_quotes(
        self,
        index_codes: list[str],
        start: date,
        end: date,
    ) -> Iterable[QuoteRow]:
        ak = _import_akshare()
        start_s = start.isoformat()
        end_s = end.isoformat()

        for code in index_codes:
            zh_name = _LG_NAME.get(code)
            sina_code = _SINA_CODE.get(code)
            try:
                if zh_name is not None:
                    # 走 lg 路径：PE + PB 10y 历史 + DY 快照
                    yield from self._fetch_one_a(ak, code, zh_name, start_s, end_s)
                elif sina_code is not None:
                    # 走 sina 路径：close 历史 + PE/DY 快照（csindex 可选）
                    yield from self._fetch_one_a_sina(ak, code, sina_code, start_s, end_s)
                else:
                    log.warning("akshare.skip_unmapped_code", code=code)
                    continue
            except Exception as e:
                log.error("akshare.fetch_failed", code=code, error=str(e))
                raise FetchFailure(f"akshare fetch failed for {code}: {e}") from e

    def _fetch_one_a(
        self,
        ak,  # noqa: ANN001
        code: str,
        zh_name: str,
        start_s: str,
        end_s: str,
    ) -> Iterable[QuoteRow]:
        pe_df = ak.stock_index_pe_lg(symbol=zh_name)
        pb_df = ak.stock_index_pb_lg(symbol=zh_name)

        pe_df = pe_df.rename(
            columns={
                "日期": "date",
                "指数": "close",
                "滚动市盈率": "pe_ttm",
                "静态市盈率": "pe_static",
            }
        )[["date", "close", "pe_ttm"]]
        pe_df["date"] = pe_df["date"].astype(str)

        pb_df = pb_df.rename(columns={"日期": "date", "市净率": "pb"})[["date", "pb"]]
        pb_df["date"] = pb_df["date"].astype(str)

        df = pe_df.merge(pb_df, on="date", how="left")

        # SRS R2：股息率快照（最近 20 天），按日期 left-join；历史早期保持 None
        dy_by_date = self._fetch_dividend_yield_snapshot(ak, code)
        df["dividend_yield"] = df["date"].map(dy_by_date)

        mask = (df["date"] >= start_s) & (df["date"] <= end_s)
        df = df.loc[mask].copy()

        for _, row in df.iterrows():
            yield QuoteRow(
                index_code=code,
                date=row["date"],
                close=to_decimal(row.get("close")) or Decimal(0),
                pe_ttm=to_decimal(row.get("pe_ttm")),
                pb=to_decimal(row.get("pb")),
                dividend_yield=to_decimal(row.get("dividend_yield")),
                source=self.name,
            )

    def _fetch_dividend_yield_snapshot(self, ak, code: str) -> dict[str, Decimal]:  # noqa: ANN001
        """中证指数公司股息率快照（最近 20 个交易日）。

        非中证编制（如创业板 50）返回空 dict；接口失败也返回空，不阻塞 PE/PB 入库。
        返回值：{date_str: Decimal(股息率小数)}；股息率从百分数（如 2.5）转为 0.025。
        """
        csi_code = _CSINDEX_CODE.get(code)
        if csi_code is None:
            return {}
        try:
            df = ak.stock_zh_index_value_csindex(symbol=csi_code)
        except Exception as e:
            log.warning("akshare.dy_snapshot_failed", code=code, error=str(e)[:100])
            return {}
        out: dict[str, Decimal] = {}
        for _, row in df.iterrows():
            d = str(row.get("日期"))
            dy = to_decimal(row.get("股息率1"))
            if dy is not None:
                out[d] = dy / Decimal(100)
        return out

    def _fetch_csindex_pe_snapshot(self, ak, code: str) -> dict[str, Decimal]:  # noqa: ANN001
        """中证指数公司 PE-TTM 快照（最近 20 个交易日，市盈率1 列）。

        与 _fetch_dividend_yield_snapshot 配对使用，给非 lg 池的指数提供估值快照。
        非中证编制返回空 dict。
        """
        csi_code = _CSINDEX_CODE.get(code)
        if csi_code is None:
            return {}
        try:
            df = ak.stock_zh_index_value_csindex(symbol=csi_code)
        except Exception as e:
            log.warning("akshare.pe_snapshot_failed", code=code, error=str(e)[:100])
            return {}
        out: dict[str, Decimal] = {}
        for _, row in df.iterrows():
            d = str(row.get("日期"))
            pe = to_decimal(row.get("市盈率1"))
            if pe is not None:
                out[d] = pe
        return out

    def _fetch_one_a_sina(
        self,
        ak,  # noqa: ANN001
        code: str,
        sina_code: str,
        start_s: str,
        end_s: str,
    ) -> Iterable[QuoteRow]:
        """lg 池外的 A 股指数路径：新浪 close 历史 + csindex PE/DY 快照（可选）。

        SRS R8（M3 末）：非 lg 池指数无 PE/PB 历史 → 仅当前快照；
        历史早期 pe_ttm/dividend_yield 为 None，R7 阈值守住不出伪信号。
        """
        df = ak.stock_zh_index_daily(symbol=sina_code)
        df["date"] = df["date"].astype(str)

        # PE / DY 快照（仅 20 天；非中证编制返回空）
        pe_by_date = self._fetch_csindex_pe_snapshot(ak, code)
        dy_by_date = self._fetch_dividend_yield_snapshot(ak, code)
        df["pe_ttm"] = df["date"].map(pe_by_date)
        df["dividend_yield"] = df["date"].map(dy_by_date)

        mask = (df["date"] >= start_s) & (df["date"] <= end_s)
        df = df.loc[mask].copy()

        for _, row in df.iterrows():
            yield QuoteRow(
                index_code=code,
                date=row["date"],
                close=to_decimal(row.get("close")) or Decimal(0),
                pe_ttm=to_decimal(row.get("pe_ttm")),
                pb=None,                                       # csindex 不提供 PB
                dividend_yield=to_decimal(row.get("dividend_yield")),
                source=self.name,
            )

    def fetch_calendar(self, market: str, year: int) -> list[tuple[str, bool]]:
        if market != "A":
            return []
        ak = _import_akshare()
        try:
            df = ak.tool_trade_date_hist_sina()
        except Exception as e:
            raise FetchFailure(f"akshare calendar failed: {e}") from e
        df["trade_date"] = df["trade_date"].astype(str)
        days = df["trade_date"].tolist()
        return [(d, True) for d in days if d.startswith(str(year))]

    def health_check(self) -> bool:
        try:
            ak = _import_akshare()
            df = ak.stock_index_pe_lg(symbol="沪深300")
            return len(df) > 0
        except Exception:
            return False
