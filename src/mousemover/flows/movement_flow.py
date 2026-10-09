"""Threaded movement workflow communicating through a UI-safe queue."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

from mousemover.logging_config import get_logger
from mousemover.modules.movement import MouseMover, MovementSettings


@dataclass(frozen=True, slots=True)
class FlowEvent:
    kind: str
    value: Any = None


class MovementFlow:
    def __init__(self, mover: MouseMover, events: queue.Queue[FlowEvent]) -> None:
        self._mover = mover
        self._events = events
        self._stop_event = threading.Event()
        self._timer_expired = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._logger = get_logger(__name__)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, settings: MovementSettings) -> None:
        settings.validate()
        with self._lock:
            if self.is_running:
                raise RuntimeError("鼠标移动任务已经在运行")
            self._stop_event = threading.Event()
            self._timer_expired = threading.Event()
            self._thread = threading.Thread(
                target=self._run,
                args=(settings,),
                name="mouse-mover-worker",
                daemon=True,
            )
            self._thread.start()

    def cancel(self) -> None:
        if self.is_running:
            self._events.put(FlowEvent("status", "正在取消"))
            self._stop_event.set()

    def _run(self, settings: MovementSettings) -> None:
        started = time.monotonic()
        timer = threading.Thread(
            target=self._report_time,
            args=(started, settings.duration_seconds),
            name="mouse-mover-timer",
            daemon=True,
        )
        timer.start()
        self._events.put(FlowEvent("started"))
        self._events.put(FlowEvent("log", "鼠标移动已启动"))
        self._logger.info("鼠标移动已启动")
        try:
            self._mover.run(settings, self._stop_event)
            state = "完成" if self._timer_expired.is_set() else "已取消"
            self._events.put(FlowEvent("finished", state))
            self._events.put(FlowEvent("log", f"任务{state}"))
            self._logger.info("鼠标移动任务%s", state)
        except Exception as exc:
            self._logger.exception("鼠标移动任务失败")
            self._events.put(FlowEvent("failed", str(exc)))
        finally:
            self._stop_event.set()

    def _report_time(self, started: float, duration: int | None) -> None:
        while not self._stop_event.wait(0.2):
            elapsed = int(time.monotonic() - started)
            if duration is not None and elapsed >= duration:
                self._timer_expired.set()
                self._stop_event.set()
                break
            remaining = None if duration is None else max(0, duration - elapsed)
            self._events.put(FlowEvent("tick", (elapsed, remaining)))
