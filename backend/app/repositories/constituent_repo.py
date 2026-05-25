"""SRS v1.1.0 方案 A：IndexConstituent + IndexConstituentQuote 仓储。"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IndexConstituent, IndexConstituentQuote
from app.utils.time_utils import now_iso


# ============ IndexConstituent（成分股权重）============
def upsert_constituent(
    session: Session, index_id: int, date_: str, stock_code: str, weight: Decimal,
) -> bool:
    existing = session.scalar(
        select(IndexConstituent).where(
            IndexConstituent.index_id == index_id,
            IndexConstituent.date == date_,
            IndexConstituent.stock_code == stock_code,
        )
    )
    if existing is None:
        session.add(IndexConstituent(
            index_id=index_id, date=date_, stock_code=stock_code,
            weight=weight, created_at=now_iso(),
        ))
        return True
    if existing.weight != weight:
        existing.weight = weight
        return True
    return False


def get_weights_on(session: Session, index_id: int, date_: str) -> list[IndexConstituent]:
    """取距 date_ 最近的（≤）一次月度报告的成分股权重。

    用于 forward-fill：交易日 d 应用最近一次月度权重。
    """
    last_date = session.scalar(
        select(IndexConstituent.date)
        .where(IndexConstituent.index_id == index_id)
        .where(IndexConstituent.date <= date_)
        .order_by(IndexConstituent.date.desc()).limit(1)
    )
    if last_date is None:
        return []
    return list(session.scalars(
        select(IndexConstituent)
        .where(IndexConstituent.index_id == index_id, IndexConstituent.date == last_date)
    ))


def list_distinct_stock_codes(session: Session, index_id: int) -> list[str]:
    """该指数 10y 累计出现过的所有成分股代码（含调样）。

    用于 daily_basic 批量拉取。
    """
    rows = session.execute(
        select(IndexConstituent.stock_code).where(IndexConstituent.index_id == index_id).distinct()
    ).all()
    return [r[0] for r in rows]


def list_report_dates(session: Session, index_id: int) -> list[str]:
    rows = session.execute(
        select(IndexConstituent.date).where(IndexConstituent.index_id == index_id).distinct()
    ).all()
    return sorted([r[0] for r in rows])


# ============ IndexConstituentQuote（成分股日频）============
def upsert_quote(
    session: Session, stock_code: str, date_: str, *,
    total_mv: Decimal | None, pe_ttm: Decimal | None, pb: Decimal | None,
    source: str = "tushare",
) -> bool:
    existing = session.scalar(
        select(IndexConstituentQuote).where(
            IndexConstituentQuote.stock_code == stock_code,
            IndexConstituentQuote.date == date_,
        )
    )
    if existing is None:
        session.add(IndexConstituentQuote(
            stock_code=stock_code, date=date_,
            total_mv=total_mv, pe_ttm=pe_ttm, pb=pb,
            source=source, created_at=now_iso(),
        ))
        return True
    changed = False
    if existing.total_mv != total_mv:
        existing.total_mv = total_mv; changed = True
    if existing.pe_ttm != pe_ttm:
        existing.pe_ttm = pe_ttm; changed = True
    if existing.pb != pb:
        existing.pb = pb; changed = True
    return changed


def get_quote(session: Session, stock_code: str, date_: str) -> IndexConstituentQuote | None:
    return session.scalar(
        select(IndexConstituentQuote)
        .where(IndexConstituentQuote.stock_code == stock_code, IndexConstituentQuote.date == date_)
    )


def get_quotes_batch(
    session: Session, stock_codes: list[str], date_: str,
) -> dict[str, IndexConstituentQuote]:
    rows = session.scalars(
        select(IndexConstituentQuote)
        .where(IndexConstituentQuote.stock_code.in_(stock_codes))
        .where(IndexConstituentQuote.date == date_)
    )
    return {r.stock_code: r for r in rows}


def has_data(session: Session, stock_code: str) -> bool:
    return session.scalar(
        select(IndexConstituentQuote.id).where(IndexConstituentQuote.stock_code == stock_code).limit(1)
    ) is not None
