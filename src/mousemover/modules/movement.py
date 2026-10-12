"""Pure movement settings and a stoppable mouse movement loop."""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from math import hypot
from typing import Any

from mousemover.modules.mouse_backend import MouseBackend


@dataclass(frozen=True, slots=True)
class MovementSettings:
    delay_seconds: float
    offset_pixels: int
    movement_duration_seconds: float = 0.4
    random_movement: bool = False
    minimum_pixels: int = 5
    maximum_pixels: int = 40
    random_delay: bool = False
    minimum_delay_seconds: float = 0
    maximum_delay_seconds: float = 10
    random_area_width: int = 400
    random_area_height: int = 300
    manual_move_threshold_pixels: int = 60
    manual_idle_seconds: float = 3
    duration_seconds: int | None = None

    def validate(self) -> None:
        if self.delay_seconds < 0.1:
            raise ValueError("移动间隔不能小于 0.1 秒")
        if self.offset_pixels < 1:
            raise ValueError("移动距离必须至少为 1 像素")
        if not 0.05 <= self.movement_duration_seconds <= 5:
            raise ValueError("单程移动耗时必须在 0.05 到 5 秒之间")
        if self.minimum_pixels < 1 or self.maximum_pixels < self.minimum_pixels:
            raise ValueError("随机移动范围无效")
        if self.minimum_delay_seconds < 0 or self.maximum_delay_seconds < self.minimum_delay_seconds:
            raise ValueError("随机延迟范围无效")
        if self.random_area_width < 20 or self.random_area_height < 20:
            raise ValueError("随机移动范围的宽度和高度必须至少为 20 像素")
        if self.manual_move_threshold_pixels < 10:
            raise ValueError("人工移动检测阈值必须至少为 10 像素")
        if not 0.5 <= self.manual_idle_seconds <= 60:
            raise ValueError("人工操作结束等待时间必须在 0.5 到 60 秒之间")
        if self.duration_seconds is not None and self.duration_seconds < 1:
            raise ValueError("定时运行时长必须至少为 1 秒")


class MouseMover:
    _FRAMES_PER_SECOND = 60

    def __init__(self, backend: MouseBackend, random_source: random.Random | None = None) -> None:
        self._backend = backend
        self._random = random_source or random.Random()

    def run(
        self,
        settings: MovementSettings,
        stop_event: threading.Event,
        event_callback: Callable[[str, Any], None] | None = None,
    ) -> None:
        """Move smoothly until cancellation, pausing for manual input."""
        settings.validate()
        if settings.random_movement:
            self._run_random(settings, stop_event, event_callback)
        else:
            self._run_fixed(settings, stop_event)

    def _run_fixed(self, settings: MovementSettings, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            distance = settings.offset_pixels
            dx = distance * self._random.choice((-1, 1))
            dy = distance * self._random.choice((-1, 1))
            delay = self._movement_delay(settings)

            origin = self._backend.position()
            target = (origin[0] + dx, origin[1] + dy)
            if not self._move_smoothly(
                origin,
                target,
                settings.movement_duration_seconds,
                stop_event,
            ):
                self._return_to_origin(origin, settings.movement_duration_seconds)
                return

            if stop_event.wait(delay):
                self._return_to_origin(origin, settings.movement_duration_seconds)
                return

            if not self._move_smoothly(
                target,
                origin,
                settings.movement_duration_seconds,
                stop_event,
            ):
                self._return_to_origin(origin, settings.movement_duration_seconds)
                return

            if stop_event.wait(delay):
                return

    def _run_random(
        self,
        settings: MovementSettings,
        stop_event: threading.Event,
        event_callback: Callable[[str, Any], None] | None,
    ) -> None:
        anchor = self._backend.position()
        expected = anchor
        self._emit_area(event_callback, anchor, settings)

        while not stop_event.is_set():
            actual = self._backend.position()
            if self._distance(actual, expected) >= settings.manual_move_threshold_pixels:
                resumed = self._wait_for_manual_end(settings, stop_event, event_callback)
                if resumed is None:
                    return
                anchor = resumed
                expected = anchor
                self._emit_area(event_callback, anchor, settings)
                continue

            distance = self._random.randint(settings.minimum_pixels, settings.maximum_pixels)
            dx = distance * self._random.choice((-1, 1))
            dy = distance * self._random.choice((-1, 1))
            target = self._clamp_to_area(
                (actual[0] + dx, actual[1] + dy),
                anchor,
                settings,
            )
            outcome = self._move_random_segment(actual, target, settings, stop_event)
            if outcome == "stopped":
                return
            if outcome == "manual":
                resumed = self._wait_for_manual_end(settings, stop_event, event_callback)
                if resumed is None:
                    return
                anchor = resumed
                expected = anchor
                self._emit_area(event_callback, anchor, settings)
                continue

            expected = target
            outcome = self._wait_with_manual_detection(
                self._movement_delay(settings),
                expected,
                settings,
                stop_event,
            )
            if outcome == "stopped":
                return
            if outcome == "manual":
                resumed = self._wait_for_manual_end(settings, stop_event, event_callback)
                if resumed is None:
                    return
                anchor = resumed
                expected = anchor
                self._emit_area(event_callback, anchor, settings)

    def _move_random_segment(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        settings: MovementSettings,
        stop_event: threading.Event,
    ) -> str:
        frame_count = max(2, round(settings.movement_duration_seconds * self._FRAMES_PER_SECOND))
        frame_interval = settings.movement_duration_seconds / frame_count
        expected = start
        accumulated_manual_distance = 0.0
        for frame in range(1, frame_count + 1):
            actual = self._backend.position()
            deviation = self._distance(actual, expected)
            if deviation >= 3:
                accumulated_manual_distance += deviation
            else:
                accumulated_manual_distance = max(0.0, accumulated_manual_distance - 3)
            if (
                deviation >= settings.manual_move_threshold_pixels
                or accumulated_manual_distance >= settings.manual_move_threshold_pixels
            ):
                return "manual"
            progress = frame / frame_count
            eased = progress * progress * (3 - 2 * progress)
            expected = (
                start[0] + ((end[0] - start[0]) * eased),
                start[1] + ((end[1] - start[1]) * eased),
            )
            self._backend.move_to(*expected)
            if frame < frame_count and stop_event.wait(frame_interval):
                return "stopped"
        return "completed"

    def _wait_with_manual_detection(
        self,
        duration: float,
        expected: tuple[float, float],
        settings: MovementSettings,
        stop_event: threading.Event,
    ) -> str:
        remaining = duration
        while remaining > 0:
            interval = min(0.05, remaining)
            if stop_event.wait(interval):
                return "stopped"
            if self._distance(self._backend.position(), expected) >= settings.manual_move_threshold_pixels:
                return "manual"
            remaining -= interval
        return "completed"

    def _wait_for_manual_end(
        self,
        settings: MovementSettings,
        stop_event: threading.Event,
        event_callback: Callable[[str, Any], None] | None,
    ) -> tuple[float, float] | None:
        current = self._backend.position()
        self._emit(event_callback, "manual_started", {"position": current})
        last_active_position = current
        idle_started = time.monotonic()
        while not stop_event.wait(0.05):
            current = self._backend.position()
            if self._distance(current, last_active_position) >= 2:
                last_active_position = current
                idle_started = time.monotonic()
            if time.monotonic() - idle_started >= settings.manual_idle_seconds:
                self._emit(event_callback, "manual_ended", {"position": current})
                return current
        return None

    def _movement_delay(self, settings: MovementSettings) -> float:
        delay = settings.delay_seconds
        if settings.random_delay:
            delay += self._random.uniform(
                settings.minimum_delay_seconds,
                settings.maximum_delay_seconds,
            )
        return delay

    @staticmethod
    def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
        return hypot(first[0] - second[0], first[1] - second[1])

    @staticmethod
    def _clamp_to_area(
        point: tuple[float, float],
        anchor: tuple[float, float],
        settings: MovementSettings,
    ) -> tuple[float, float]:
        half_width = settings.random_area_width / 2
        half_height = settings.random_area_height / 2
        return (
            min(max(point[0], anchor[0] - half_width), anchor[0] + half_width),
            min(max(point[1], anchor[1] - half_height), anchor[1] + half_height),
        )

    @staticmethod
    def _emit_area(
        event_callback: Callable[[str, Any], None] | None,
        anchor: tuple[float, float],
        settings: MovementSettings,
    ) -> None:
        MouseMover._emit(
            event_callback,
            "movement_area",
            {
                "x": anchor[0] - (settings.random_area_width / 2),
                "y": anchor[1] - (settings.random_area_height / 2),
                "width": settings.random_area_width,
                "height": settings.random_area_height,
                "anchor": anchor,
            },
        )

    @staticmethod
    def _emit(
        event_callback: Callable[[str, Any], None] | None,
        kind: str,
        value: Any,
    ) -> None:
        if event_callback is not None:
            event_callback(kind, value)

    def _move_smoothly(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        duration: float,
        stop_event: threading.Event,
        *,
        interruptible: bool = True,
    ) -> bool:
        """Interpolate one cursor movement with eased 60 FPS updates."""
        frame_count = max(2, round(duration * self._FRAMES_PER_SECOND))
        frame_interval = duration / frame_count
        for frame in range(1, frame_count + 1):
            progress = frame / frame_count
            eased = progress * progress * (3 - 2 * progress)
            x = start[0] + ((end[0] - start[0]) * eased)
            y = start[1] + ((end[1] - start[1]) * eased)
            self._backend.move_to(x, y)
            if frame == frame_count:
                break
            if interruptible:
                if stop_event.wait(frame_interval):
                    return False
            else:
                time.sleep(frame_interval)
        return True

    def _return_to_origin(self, origin: tuple[float, float], duration: float) -> None:
        """Finish cancellation with a smooth, non-interruptible return."""
        current = self._backend.position()
        cleanup_event = threading.Event()
        self._move_smoothly(
            current,
            origin,
            duration,
            cleanup_event,
            interruptible=False,
        )
