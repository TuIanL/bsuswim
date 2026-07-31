from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from .service import execute_interpretation


class InterpretationScheduler(Protocol):
    def schedule(self, interpretation_id: int) -> None: ...


class ThreadInterpretationScheduler:
    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="report-interpretation",
        )

    def schedule(self, interpretation_id: int) -> None:
        self._executor.submit(execute_interpretation, interpretation_id)


_scheduler = ThreadInterpretationScheduler()


def schedule_interpretation(interpretation_id: int) -> None:
    _scheduler.schedule(interpretation_id)
