from pydantic import BaseModel


class SourceStatusDTO(BaseModel):
    name: str
    last_success_at: str | None
    last_error_at: str | None
    last_error_message: str | None = None


class PipelineStatusDTO(BaseModel):
    market: str
    last_run_at: str | None
    status: str
    duration_seconds: float | None
    errors: list[str] = []


class HealthResponse(BaseModel):
    sources: list[SourceStatusDTO]
    pipeline: list[PipelineStatusDTO]
