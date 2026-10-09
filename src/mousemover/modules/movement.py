"""Pure movement settings and a stoppable mouse movement loop."""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass

from mousemover.modules.mouse_backend import MouseBackend


@dataclass(frozen=True, slots=True)
class MovementSettings:
    delay_seconds: float
    offset_pixels: int
    random_movement: bool = False
    minimum_pixels: int = 5
    maximum_pixels: int = 40
    random_delay: bool = False
    minimum_delay_seconds: float = 0
    maximum_delay_seconds: float = 10
    duration_seconds: int | None = None

    def validate(self) -> None:
        if self.delay_seconds < 0.1:
            raise ValueError("移动间隔不能小于 0.1 秒")
        if self.offset_pixels < 1:
            raise ValueError("移动距离必须至少为 1 像素")
        if self.minimum_pixels < 1 or self.maximum_pixels < self.minimum_pixels:
            raise ValueError("随机移动范围无效")
        if self.minimum_delay_seconds < 0 or self.maximum_delay_seconds < self.minimum_delay_seconds:
            raise ValueError("随机延迟范围无效")
        if self.duration_seconds is not None and self.duration_seconds < 1:
            raise ValueError("定时运行时长必须至少为 1 秒")


class MouseMover:
    def __init__(self, backend: MouseBackend, random_source: random.Random | None = None) -> None:
        self._backend = backend
        self._random = random_source or random.Random()

    def run(self, settings: MovementSettings, stop_event: threading.Event) -> None:
        """Move away and back until cancellation; waits are interruptible."""
        settings.validate()
        while not stop_event.is_set():
            distance = settings.offset_pixels
            if settings.random_movement:
                distance = self._random.randint(settings.minimum_pixels, settings.maximum_pixels)
            dx = distance * self._random.choice((-1, 1))
            dy = distance * self._random.choice((-1, 1))
            delay = settings.delay_seconds
            if settings.random_delay:
                delay += self._random.uniform(
                    settings.minimum_delay_seconds,
                    settings.maximum_delay_seconds,
                )

            origin_x, origin_y = self._backend.position()
            self._backend.move_to(origin_x + dx, origin_y + dy)
            interrupted = stop_event.wait(delay)
            self._backend.move_to(origin_x, origin_y)
            if interrupted:
                return
            if stop_event.wait(delay):
                return
