from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.errors import BusinessRuleViolation, NotFound
from app.models import DCAPlan, Fund, IndexMeta
from app.repositories import dca_repo, index_repo
from app.schemas.dca import (
    DCAExecutionDTO,
    DCAPlanCreate,
    DCAPlanDTO,
    DCAPlanStatsDTO,
    DCAPlanUpdate,
    DCAStatsResponse,
    UpcomingReminderResponse,
)
from app.services import dca_planner
from app.services.valuation_service import has_enough_history
from app.utils.decimal_utils import decimal_to_str
from app.utils.time_utils import now_iso

router = APIRouter()


def _to_plan_dto(plan: DCAPlan, idx, fund) -> DCAPlanDTO:
    return DCAPlanDTO(
        id=plan.id,
        index_code=idx.code,
        index_name=idx.name,
        fund_code=fund.code if fund else None,
        fund_name=fund.name if fund else None,
        amount=decimal_to_str(plan.amount) or "0",
        frequency=plan.frequency,
        day_of_period=plan.day_of_period,
        start_date=plan.start_date,
        enabled=plan.enabled,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _to_exec_dto(e, plan, idx) -> DCAExecutionDTO:
    return DCAExecutionDTO(
        id=e.id,
        plan_id=plan.id,
        index_code=idx.code,
        index_name=idx.name,
        scheduled_date=e.scheduled_date,
        actual_date=e.actual_date,
        base_amount=decimal_to_str(e.base_amount) or "0",
        adjusted_amount=decimal_to_str(e.adjusted_amount) or "0",
        multiplier=decimal_to_str(e.multiplier) or "1",
        tier_at_decision=e.tier_at_decision,
        temperature=decimal_to_str(e.temperature) or "0",
        status=e.status,
        generated_at=e.generated_at,
        marked_at=e.marked_at,
    )


# ----- 计划 CRUD -----
@router.get("/dca-plans", response_model=list[DCAPlanDTO])
def list_dca_plans(session: Session = Depends(db_session)) -> list[DCAPlanDTO]:
    return [_to_plan_dto(p, idx, fund) for p, idx, fund in dca_repo.list_plans(session)]


@router.post("/dca-plans", response_model=DCAPlanDTO, status_code=201)
def create_dca_plan(body: DCAPlanCreate, session: Session = Depends(db_session)) -> DCAPlanDTO:
    idx = index_repo.get_by_code(session, body.index_code)
    if idx is None:
        raise NotFound("index not found", code=body.index_code)
    # 历史不足 5 年禁止绑定（SRS §9 风险表）
    if not has_enough_history(session, idx, min_years=5):
        raise BusinessRuleViolation(
            "该指数可用历史数据不足 5 年，无法绑定定投计划",
            code=body.index_code,
        )
    fund_id = None
    if body.fund_code:
        f = session.scalar(select(Fund).where(Fund.code == body.fund_code))
        if f is None:
            raise NotFound("fund not found", code=body.fund_code)
        if f.tracks_index_id != idx.id:
            raise BusinessRuleViolation(
                "fund does not track this index",
                fund_code=body.fund_code,
                index_code=body.index_code,
            )
        fund_id = f.id

    plan = DCAPlan(
        index_id=idx.id,
        fund_id=fund_id,
        amount=body.amount,
        frequency=body.frequency,
        day_of_period=body.day_of_period,
        start_date=body.start_date,
        enabled=body.enabled,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    dca_repo.add_plan(session, plan)
    dca_planner.refresh_executions_for_plan(session, plan)
    session.commit()
    fund = session.get(Fund, plan.fund_id) if plan.fund_id else None
    return _to_plan_dto(plan, idx, fund)


@router.put("/dca-plans/{plan_id}", response_model=DCAPlanDTO)
def update_dca_plan(plan_id: int, body: DCAPlanUpdate, session: Session = Depends(db_session)) -> DCAPlanDTO:
    plan = dca_repo.get_plan(session, plan_id)
    if plan is None:
        raise NotFound("plan not found", id=plan_id)
    if body.amount is not None:
        plan.amount = body.amount
    if body.frequency is not None:
        plan.frequency = body.frequency
    if body.day_of_period is not None:
        plan.day_of_period = body.day_of_period
    if body.enabled is not None:
        plan.enabled = body.enabled
    if body.fund_code is not None:
        f = session.scalar(select(Fund).where(Fund.code == body.fund_code))
        if f is None:
            raise NotFound("fund not found", code=body.fund_code)
        plan.fund_id = f.id
    plan.updated_at = now_iso()
    dca_repo.update_plan(session, plan)
    if plan.enabled:
        dca_planner.refresh_executions_for_plan(session, plan)
    session.commit()
    idx = session.get(IndexMeta, plan.index_id)
    fund = session.get(Fund, plan.fund_id) if plan.fund_id else None
    return _to_plan_dto(plan, idx, fund)


@router.delete("/dca-plans/{plan_id}", status_code=204)
def delete_dca_plan(plan_id: int, session: Session = Depends(db_session)) -> None:
    ok = dca_repo.delete_plan(session, plan_id)
    if not ok:
        raise NotFound("plan not found", id=plan_id)
    session.commit()


# ----- 执行记录 -----
@router.get("/dca-plans/{plan_id}/executions", response_model=list[DCAExecutionDTO])
def list_executions(plan_id: int, session: Session = Depends(db_session)) -> list[DCAExecutionDTO]:
    plan = dca_repo.get_plan(session, plan_id)
    if plan is None:
        raise NotFound("plan not found", id=plan_id)
    idx = session.get(IndexMeta, plan.index_id)
    rows = dca_repo.list_executions(session, plan_id)
    return [_to_exec_dto(e, plan, idx) for e in rows]


@router.post("/dca-executions/{exec_id}/mark-done", response_model=DCAExecutionDTO)
def mark_done(exec_id: int, session: Session = Depends(db_session)) -> DCAExecutionDTO:
    e = dca_repo.get_execution_by_id(session, exec_id)
    if e is None:
        raise NotFound("execution not found", id=exec_id)
    e.status = "DONE"
    e.marked_at = now_iso()
    plan = dca_repo.get_plan(session, e.plan_id)
    idx = session.get(IndexMeta, plan.index_id)
    session.commit()
    return _to_exec_dto(e, plan, idx)


@router.post("/dca-executions/{exec_id}/skip", response_model=DCAExecutionDTO)
def mark_skipped(exec_id: int, session: Session = Depends(db_session)) -> DCAExecutionDTO:
    e = dca_repo.get_execution_by_id(session, exec_id)
    if e is None:
        raise NotFound("execution not found", id=exec_id)
    e.status = "SKIPPED"
    e.marked_at = now_iso()
    plan = dca_repo.get_plan(session, e.plan_id)
    idx = session.get(IndexMeta, plan.index_id)
    session.commit()
    return _to_exec_dto(e, plan, idx)


# ----- 未来提醒 -----
@router.get("/dca-reminders/upcoming", response_model=UpcomingReminderResponse)
def upcoming_reminders(within_days: int = 7, session: Session = Depends(db_session)) -> UpcomingReminderResponse:
    rows = dca_repo.list_upcoming(session, within_days=within_days)
    return UpcomingReminderResponse(items=[_to_exec_dto(e, p, idx) for e, p, idx in rows])


# ----- 累计统计 -----
@router.get("/dca-plans/stats", response_model=DCAStatsResponse)
def get_stats(session: Session = Depends(db_session)) -> DCAStatsResponse:
    from decimal import Decimal

    plans_stats: list[DCAPlanStatsDTO] = []
    total_done = Decimal(0)
    total_skipped = Decimal(0)

    for plan, idx, _fund in dca_repo.list_plans(session):
        execs = dca_repo.list_executions(session, plan.id, limit=10000)
        done_amt = Decimal(0)
        skip_amt = Decimal(0)
        base_amt = Decimal(0)
        done_cnt = skip_cnt = pend_cnt = 0
        weighted_mul = Decimal(0)
        for e in execs:
            base_amt += e.base_amount
            if e.status == "DONE":
                done_cnt += 1
                done_amt += e.adjusted_amount
                weighted_mul += e.multiplier * e.adjusted_amount
            elif e.status == "SKIPPED":
                skip_cnt += 1
                # 跳过的金额视为"基础金额"（用户原本要投入的）
                skip_amt += e.base_amount
            else:
                pend_cnt += 1
        total_done += done_amt
        total_skipped += skip_amt
        ratio = (
            Decimal(skip_cnt) / Decimal(done_cnt + skip_cnt)
            if (done_cnt + skip_cnt) > 0
            else Decimal(0)
        )
        avg_mul = (weighted_mul / done_amt) if done_amt > 0 else Decimal(1)
        plans_stats.append(
            DCAPlanStatsDTO(
                plan_id=plan.id,
                index_code=idx.code,
                index_name=idx.name,
                done_count=done_cnt,
                skipped_count=skip_cnt,
                pending_count=pend_cnt,
                done_total_amount=decimal_to_str(done_amt.quantize(Decimal("0.01"))) or "0",
                skipped_total_amount=decimal_to_str(skip_amt.quantize(Decimal("0.01"))) or "0",
                base_total_if_no_adjustment=decimal_to_str(base_amt.quantize(Decimal("0.01"))) or "0",
                skip_ratio=decimal_to_str(ratio.quantize(Decimal("0.0001"))) or "0",
                average_multiplier=decimal_to_str(avg_mul.quantize(Decimal("0.01"))) or "1",
            )
        )
    return DCAStatsResponse(
        plans=plans_stats,
        total_done_amount=decimal_to_str(total_done.quantize(Decimal("0.01"))) or "0",
        total_skipped_amount=decimal_to_str(total_skipped.quantize(Decimal("0.01"))) or "0",
    )
