from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DCAExecution, DCAPlan, Fund, IndexMeta


def list_plans(session: Session, enabled_only: bool = False) -> list[tuple[DCAPlan, IndexMeta, Fund | None]]:
    stmt = (
        select(DCAPlan, IndexMeta).join(IndexMeta, IndexMeta.id == DCAPlan.index_id)
        .order_by(DCAPlan.id)
    )
    if enabled_only:
        stmt = stmt.where(DCAPlan.enabled == True)  # noqa: E712
    rows = session.execute(stmt).all()
    out: list[tuple[DCAPlan, IndexMeta, Fund | None]] = []
    for p, idx in rows:
        fund = session.get(Fund, p.fund_id) if p.fund_id else None
        out.append((p, idx, fund))
    return out


def get_plan(session: Session, plan_id: int) -> DCAPlan | None:
    return session.get(DCAPlan, plan_id)


def add_plan(session: Session, plan: DCAPlan) -> DCAPlan:
    session.add(plan)
    session.flush()
    return plan


def update_plan(session: Session, plan: DCAPlan) -> DCAPlan:
    """plan 已 attached + 修改完成；本函数仅 flush。"""
    session.flush()
    return plan


def delete_plan(session: Session, plan_id: int) -> bool:
    p = session.get(DCAPlan, plan_id)
    if p is None:
        return False
    # 级联删除其执行记录
    for e in session.scalars(select(DCAExecution).where(DCAExecution.plan_id == plan_id)).all():
        session.delete(e)
    session.delete(p)
    return True


def list_executions(session: Session, plan_id: int, limit: int = 50) -> list[DCAExecution]:
    return list(
        session.scalars(
            select(DCAExecution)
            .where(DCAExecution.plan_id == plan_id)
            .order_by(DCAExecution.actual_date.desc())
            .limit(limit)
        )
    )


def get_execution_by_id(session: Session, exec_id: int) -> DCAExecution | None:
    return session.get(DCAExecution, exec_id)


def get_execution(session: Session, plan_id: int, actual_date: str) -> DCAExecution | None:
    return session.scalar(
        select(DCAExecution).where(
            DCAExecution.plan_id == plan_id, DCAExecution.actual_date == actual_date
        )
    )


def upsert_execution(session: Session, e: DCAExecution) -> tuple[bool, DCAExecution]:
    """返回 (is_new, execution)。已存在的 PENDING 状态会被覆盖；DONE/SKIPPED 不再改。"""
    existing = get_execution(session, e.plan_id, e.actual_date)
    if existing is None:
        session.add(e)
        session.flush()
        return True, e
    if existing.status == "PENDING":
        existing.base_amount = e.base_amount
        existing.adjusted_amount = e.adjusted_amount
        existing.multiplier = e.multiplier
        existing.tier_at_decision = e.tier_at_decision
        existing.temperature = e.temperature
        existing.generated_at = e.generated_at
    return False, existing


def list_upcoming(session: Session, within_days: int = 7) -> list[tuple[DCAExecution, DCAPlan, IndexMeta]]:
    """未来 N 天内 status=PENDING 的执行记录。"""
    from datetime import date, timedelta

    today = date.today().isoformat()
    end = (date.today() + timedelta(days=within_days)).isoformat()
    rows = session.execute(
        select(DCAExecution, DCAPlan, IndexMeta)
        .join(DCAPlan, DCAPlan.id == DCAExecution.plan_id)
        .join(IndexMeta, IndexMeta.id == DCAPlan.index_id)
        .where(
            DCAExecution.status == "PENDING",
            DCAExecution.actual_date >= today,
            DCAExecution.actual_date <= end,
        )
        .order_by(DCAExecution.actual_date)
    ).all()
    return [(r[0], r[1], r[2]) for r in rows]
