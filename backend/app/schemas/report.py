from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ReportGenerate(BaseModel):
    session_id: int


class ReportData(BaseModel):
    session_id: int
    task_id: int
    source: str
    generated_at: datetime
    report: dict[str, Any]
