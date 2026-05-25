"""数据源 + 调度健康面板。

M1：先用内存状态记录最近一次结果；后续可持久化到表中。
"""
from __future__ import annotations

import threading
from dataclasses import asdict, dataclass


@dataclass
class SourceStatus:
    name: str
    last_success_at: str | None = None
    last_error_at: str | None = None
    last_error_message: str | None = None


@dataclass
class PipelineStatus:
    market: str
    last_run_at: str | None = None
    status: str = "UNKNOWN"  # SUCCESS / PARTIAL / FAILED
    duration_seconds: float | None = None
    errors: list[str] | None = None


class _HealthState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.sources: dict[str, SourceStatus] = {}
        self.pipeline: dict[str, PipelineStatus] = {}

    def record_source_success(self, name: str, at: str) -> None:
        with self._lock:
            s = self.sources.setdefault(name, SourceStatus(name=name))
            s.last_success_at = at

    def record_source_failure(self, name: str, at: str, msg: str) -> None:
        with self._lock:
            s = self.sources.setdefault(name, SourceStatus(name=name))
            s.last_error_at = at
            s.last_error_message = msg

    def record_pipeline(
        self,
        market: str,
        last_run_at: str,
        status: str,
        duration_seconds: float,
        errors: list[str] | None = None,
    ) -> None:
        with self._lock:
            self.pipeline[market] = PipelineStatus(
                market=market,
                last_run_at=last_run_at,
                status=status,
                duration_seconds=duration_seconds,
                errors=errors or [],
            )

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "sources": [asdict(s) for s in self.sources.values()],
                "pipeline": [asdict(p) for p in self.pipeline.values()],
            }


_state = _HealthState()


def state() -> _HealthState:
    return _state
