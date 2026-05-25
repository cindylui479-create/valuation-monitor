from __future__ import annotations

from fastapi import APIRouter

from app.schemas.health import HealthResponse, PipelineStatusDTO, SourceStatusDTO
from app.services.health_service import state

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    snap = state().snapshot()
    return HealthResponse(
        sources=[SourceStatusDTO(**s) for s in snap["sources"]],
        pipeline=[PipelineStatusDTO(**p) for p in snap["pipeline"]],
    )


@router.get("/health/pipeline", response_model=list[PipelineStatusDTO])
def get_pipeline_status() -> list[PipelineStatusDTO]:
    snap = state().snapshot()
    return [PipelineStatusDTO(**p) for p in snap["pipeline"]]
