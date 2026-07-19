"""Pipeline protocol and outcome types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class PipelineOutcome:
    task_id: int
    pipeline_type: str
    pipeline_version: str
    completed: bool
    report_id: int | None = None


@runtime_checkable
class AnalysisPipeline(Protocol):
    pipeline_type: str
    supported_versions: set[str]

    async def run(self, task_id: int, pipeline_version: str) -> PipelineOutcome:
        ...
