"""数据质量验证：把 DB 里的当日 PE-TTM / PB 与多源原始数据对比，找差异。

来源（独立）：
  A. DB（我们存的）          —— index_quote 表最新一行
  B. 乐咕乐股 stock_index_pe_lg / pb_lg  —— A 股宽基 + 主题，最近一行
  C. 中证指数公司 stock_zh_index_value_csindex —— 中证编制指数，最近 20 天快照
  D. Tushare Pro index_dailybasic —— 部分 A 股宽基/综合指数

差异容忍：
  - |Δ| < 0.5% 视为"一致"
  - 0.5% ~ 2% 视为"小差"（不同源口径细节差异）
  - > 2% 视为"显著不一致"，可能数据出错

用法：python -m scripts.verify_data_quality
"""
from __future__ import annotations

import sys
from decimal import Decimal
from typing import Optional

import akshare as ak

from app.adapters.akshare_adapter import _CSINDEX_CODE, _LG_NAME
from app.config import get_settings
from app.db import SessionLocal
from app.models import IndexMeta, IndexQuote, Market
from app.utils.decimal_utils import to_decimal
from sqlalchemy import select


def fetch_lg_latest(code: str) -> dict[str, Optional[Decimal]]:
    """乐咕乐股最新 PE/PB。"""
    zh_name = _LG_NAME.get(code)
    if zh_name is None:
        return {"pe": None, "pb": None}
    try:
        pe_df = ak.stock_index_pe_lg(symbol=zh_name)
        pb_df = ak.stock_index_pb_lg(symbol=zh_name)
        pe = to_decimal(pe_df.iloc[-1].get("滚动市盈率"))
        pb = to_decimal(pb_df.iloc[-1].get("市净率"))
        date = str(pe_df.iloc[-1].get("日期"))
        return {"pe": pe, "pb": pb, "date": date}
    except Exception as e:
        return {"pe": None, "pb": None, "error": str(e)[:80]}


def fetch_csindex_latest(code: str) -> dict[str, Optional[Decimal]]:
    """中证指数公司最近一行 PE / 股息率。"""
    csi_code = _CSINDEX_CODE.get(code)
    if csi_code is None:
        return {"pe": None}
    try:
        df = ak.stock_zh_index_value_csindex(symbol=csi_code)
        if df.empty:
            return {"pe": None}
        last = df.iloc[0]  # 该接口最新在前
        pe = to_decimal(last.get("市盈率1"))
        dy = to_decimal(last.get("股息率1"))
        date = str(last.get("日期"))
        return {"pe": pe, "dy_pct": dy, "date": date}
    except Exception as e:
        return {"pe": None, "error": str(e)[:80]}


def fetch_tushare_latest(code: str) -> dict[str, Optional[Decimal]]:
    """Tushare 最近一行 PE / PB。"""
    settings = get_settings()
    token = (settings.tushare_token or "").strip()
    if not token:
        return {"pe": None, "pb": None}
    try:
        import tushare as ts
        ts.set_token(token)
        pro = ts.pro_api(timeout=60)
        from datetime import date, timedelta
        end = date.today().strftime("%Y%m%d")
        start = (date.today() - timedelta(days=14)).strftime("%Y%m%d")
        df = pro.index_dailybasic(ts_code=code, start_date=start, end_date=end)
        if df is None or df.empty:
            return {"pe": None, "pb": None}
        last = df.iloc[0]  # 最新在前
        return {
            "pe": to_decimal(last.get("pe_ttm")),
            "pb": to_decimal(last.get("pb")),
            "date": str(last.get("trade_date")),
        }
    except Exception as e:
        return {"pe": None, "pb": None, "error": str(e)[:80]}


def diff_pct(a: Optional[Decimal], b: Optional[Decimal]) -> Optional[float]:
    """相对差异（%），以 a 为基准；任一为 None 返回 None。"""
    if a is None or b is None or a == 0:
        return None
    return float(abs(a - b) / abs(a) * 100)


def severity(pct: Optional[float]) -> str:
    if pct is None:
        return "—"
    if pct < 0.5:
        return "✓"            # 一致
    if pct < 2.0:
        return "·"            # 小差
    return "‼"                  # 显著不一致


def main() -> int:
    with SessionLocal() as session:
        a_market = session.scalar(select(Market).where(Market.code == "A"))
        if a_market is None:
            print("no A market seeded")
            return 1

        indices = list(session.scalars(
            select(IndexMeta).where(IndexMeta.market_id == a_market.id).order_by(IndexMeta.code)
        ))

        print(f"{'指数':14}{'名称':14}{'DB-PE':>8}{'DB-PB':>8}"
              f"{'LG-PE':>8}{'Δ':>4}{'CSI-PE':>9}{'Δ':>4}"
              f"{'TS-PE':>8}{'Δ':>4}{'TS-PB':>8}{'Δ':>5}")
        print("-" * 105)

        any_anomaly = False
        for idx in indices:
            # DB 当前
            q = session.scalar(
                select(IndexQuote)
                .where(IndexQuote.index_id == idx.id)
                .order_by(IndexQuote.date.desc())
                .limit(1)
            )
            if q is None:
                continue
            db_pe = q.pe_ttm
            db_pb = q.pb

            # 三方数据
            lg = fetch_lg_latest(idx.code)
            csi = fetch_csindex_latest(idx.code)
            ts = fetch_tushare_latest(idx.code)

            lg_diff = diff_pct(db_pe, lg.get("pe"))
            csi_diff = diff_pct(db_pe, csi.get("pe"))
            ts_pe_diff = diff_pct(db_pe, ts.get("pe"))
            ts_pb_diff = diff_pct(db_pb, ts.get("pb"))

            db_pe_s = f"{float(db_pe):.2f}" if db_pe else "—"
            db_pb_s = f"{float(db_pb):.2f}" if db_pb else "—"
            lg_pe_s = f"{float(lg['pe']):.2f}" if lg.get("pe") else "—"
            csi_pe_s = f"{float(csi['pe']):.2f}" if csi.get("pe") else "—"
            ts_pe_s = f"{float(ts['pe']):.2f}" if ts.get("pe") else "—"
            ts_pb_s = f"{float(ts['pb']):.2f}" if ts.get("pb") else "—"

            print(
                f"  {idx.code:12}{idx.name:14}{db_pe_s:>8}{db_pb_s:>8}"
                f"{lg_pe_s:>8}{severity(lg_diff):>4}"
                f"{csi_pe_s:>9}{severity(csi_diff):>4}"
                f"{ts_pe_s:>8}{severity(ts_pe_diff):>4}"
                f"{ts_pb_s:>8}{severity(ts_pb_diff):>5}"
            )
            if any(d is not None and d > 2.0 for d in (lg_diff, csi_diff, ts_pe_diff, ts_pb_diff)):
                any_anomaly = True

        print()
        print("图例：✓ 差异 < 0.5% 一致 | · 0.5–2% 小差 | ‼ > 2% 显著不一致 | — 无数据")
        if any_anomaly:
            print()
            print("⚠ 有显著不一致项；请检查上面 ‼ 标记的指数。")
        return 0


if __name__ == "__main__":
    sys.exit(main())
