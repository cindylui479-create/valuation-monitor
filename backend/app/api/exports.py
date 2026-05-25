"""CSV 导出（SRS FR-6）。"""
from __future__ import annotations

import csv
import io
from datetime import date as date_t

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.deps import db_session
from app.errors import NotFound
from app.repositories import index_repo, quote_repo, valuation_repo
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


@router.get("/exports/index/{code}.csv")
def export_index_csv(
    code: str,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    window: str = Query(default="10y", pattern=r"^(5y|10y|all)$"),
    session: Session = Depends(db_session),
):
    idx = index_repo.get_by_code(session, code)
    if idx is None:
        raise NotFound("index not found", code=code)

    quotes = quote_repo.list_recent(session, idx.id, limit=10_000)
    quotes.sort(key=lambda q: q.date)
    if start:
        quotes = [q for q in quotes if q.date >= start]
    if end:
        quotes = [q for q in quotes if q.date <= end]

    val_rows = valuation_repo.series(session, idx.id, window=window, start=start, end=end)
    val_by_date = {v.date: v for v in val_rows}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "date", "close",
            "pe_ttm", "pb", "dividend_yield",
            "pe_percentile", "pb_percentile", "dy_percentile",
            "temperature", "tier",
            "source",
        ]
    )
    for q in quotes:
        v = val_by_date.get(q.date)
        writer.writerow([
            q.date,
            decimal_to_str(q.close) or "",
            decimal_to_str(q.pe_ttm) or "",
            decimal_to_str(q.pb) or "",
            decimal_to_str(q.dividend_yield) or "",
            decimal_to_str(v.pe_percentile) if v else "",
            decimal_to_str(v.pb_percentile) if v else "",
            decimal_to_str(v.dy_percentile) if v else "",
            decimal_to_str(v.temperature) if v else "",
            (v.tier if v else "") or "",
            q.source or "",
        ])

    safe_code = idx.code.replace("/", "_").replace("^", "")
    fname = f"{safe_code}_{window}_{date_t.today().isoformat()}.csv"
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
