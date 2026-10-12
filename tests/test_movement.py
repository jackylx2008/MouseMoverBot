from __future__ import annotations

import random
import threading
import unittest

from mousemover.modules.movement import MouseMover, MovementSettings


class FakeBackend:
    def __init__(self) -> None:
        self.current = (100.0, 100.0)
        self.moves: list[tuple[float, float]] = []

    def position(self) -> tuple[float, float]:
        return self.current

    def move_to(self, x: float, y: float) -> None:
        self.current = (x, y)
        self.moves.append(self.current)


class ManualJumpBackend(FakeBackend):
    def __init__(self) -> None:
        super().__init__()
        self.reads = 0

    def position(self) -> tuple[float, float]:
        self.reads += 1
        if self.reads == 4:
            self.current = (250.0, 260.0)
        return self.current


class GradualManualMoveBackend(FakeBackend):
    def __init__(self) -> None:
        super().__init__()
        self.manual_steps_remaining = 0

    def position(self) -> tuple[float, float]:
        if self.manual_steps_remaining:
            self.current = (self.current[0] + 8, self.current[1])
            self.manual_steps_remaining -= 1
        return self.current

    def move_to(self, x: float, y: float) -> None:
        super().move_to(x, y)
        if len(self.moves) == 1:
            self.manual_steps_remaining = 4


class StopAfterWaits:
    def __init__(self, maximum_waits: int) -> None:
        self.calls = 0
        self.maximum_waits = maximum_waits

    def is_set(self) -> bool:
        return self.calls >= self.maximum_waits

    def wait(self, timeout: float) -> bool:
        self.calls += 1
        return self.calls >= self.maximum_waits


class MovementTests(unittest.TestCase):
    def test_moves_continuously_then_returns_to_origin(self) -> None:
        backend = FakeBackend()
        mover = MouseMover(backend, random.Random(4))
        settings = MovementSettings(
            delay_seconds=0.1,
            offset_pixels=10,
            movement_duration_seconds=0.1,
        )
        mover.run(settings, StopAfterWaits(12))  # type: ignore[arg-type]
        self.assertEqual(len(backend.moves), 12)
        self.assertNotEqual(backend.moves[0], backend.moves[5])
        self.assertEqual(backend.moves[-1], (100.0, 100.0))

    def test_invalid_delay_is_rejected(self) -> None:
        settings = MovementSettings(delay_seconds=0, offset_pixels=10)
        with self.assertRaisesRegex(ValueError, "移动间隔"):
            settings.validate()

    def test_invalid_movement_duration_is_rejected(self) -> None:
        settings = MovementSettings(
            delay_seconds=1,
            offset_pixels=10,
            movement_duration_seconds=0.01,
        )
        with self.assertRaisesRegex(ValueError, "单程移动耗时"):
            settings.validate()

    def test_cancelled_movement_returns_smoothly_to_origin(self) -> None:
        backend = FakeBackend()
        settings = MovementSettings(
            delay_seconds=0.1,
            offset_pixels=10,
            movement_duration_seconds=0.05,
        )
        MouseMover(backend, random.Random(4)).run(
            settings,
            StopAfterWaits(2),  # type: ignore[arg-type]
        )
        self.assertGreater(len(backend.moves), 3)
        self.assertEqual(backend.moves[-1], (100.0, 100.0))

    def test_random_movement_continues_from_current_position(self) -> None:
        backend = FakeBackend()
        settings = MovementSettings(
            delay_seconds=0.1,
            offset_pixels=10,
            movement_duration_seconds=0.1,
            random_movement=True,
            minimum_pixels=10,
            maximum_pixels=10,
        )
        MouseMover(backend, random.Random(4)).run(
            settings,
            StopAfterWaits(12),  # type: ignore[arg-type]
        )
        first_target = backend.moves[5]
        second_start = backend.moves[6]
        self.assertNotEqual(first_target, (100.0, 100.0))
        self.assertNotEqual(second_start, (100.0, 100.0))
        self.assertNotEqual(backend.moves[-1], (100.0, 100.0))

    def test_cancelled_random_movement_does_not_return_to_anchor(self) -> None:
        backend = FakeBackend()
        settings = MovementSettings(
            delay_seconds=0.1,
            offset_pixels=10,
            movement_duration_seconds=0.05,
            random_movement=True,
            minimum_pixels=10,
            maximum_pixels=10,
        )
        MouseMover(backend, random.Random(4)).run(
            settings,
            StopAfterWaits(2),  # type: ignore[arg-type]
        )
        self.assertEqual(len(backend.moves), 2)
        self.assertNotEqual(backend.moves[-1], (100.0, 100.0))

    def test_manual_movement_pauses_and_reanchors_random_area(self) -> None:
        backend = ManualJumpBackend()
        settings = MovementSettings(
            delay_seconds=0.1,
            offset_pixels=10,
            movement_duration_seconds=0.05,
            random_movement=True,
            minimum_pixels=10,
            maximum_pixels=10,
            random_area_width=200,
            random_area_height=100,
            manual_move_threshold_pixels=20,
            manual_idle_seconds=0.5,
        )
        events: list[tuple[str, object, int]] = []
        stop = threading.Event()
        timer = threading.Timer(1.0, stop.set)
        timer.start()
        try:
            MouseMover(backend, random.Random(4)).run(
                settings,
                stop,
                lambda kind, value: events.append((kind, value, len(backend.moves))),
            )
        finally:
            timer.cancel()

        kinds = [kind for kind, _, _ in events]
        self.assertIn("manual_started", kinds)
        self.assertIn("manual_ended", kinds)
        areas = [(value, move_index) for kind, value, move_index in events if kind == "movement_area"]
        self.assertGreaterEqual(len(areas), 2)
        self.assertEqual(areas[1][0]["anchor"], (250.0, 260.0))  # type: ignore[index]
        resumed_moves = backend.moves[areas[1][1] :]
        self.assertTrue(resumed_moves)
        self.assertTrue(all(150 <= x <= 350 and 210 <= y <= 310 for x, y in resumed_moves))

    def test_random_movement_is_clamped_to_configured_area(self) -> None:
        backend = FakeBackend()
        settings = MovementSettings(
            delay_seconds=0.1,
            offset_pixels=10,
            movement_duration_seconds=0.05,
            random_movement=True,
            minimum_pixels=40,
            maximum_pixels=40,
            random_area_width=20,
            random_area_height=20,
            manual_move_threshold_pixels=100,
        )
        MouseMover(backend, random.Random(4)).run(
            settings,
            StopAfterWaits(20),  # type: ignore[arg-type]
        )
        self.assertTrue(backend.moves)
        self.assertTrue(all(90 <= x <= 110 and 90 <= y <= 110 for x, y in backend.moves))

    def test_gradual_manual_movement_is_accumulated_during_animation(self) -> None:
        backend = GradualManualMoveBackend()
        settings = MovementSettings(
            delay_seconds=0.1,
            offset_pixels=10,
            movement_duration_seconds=0.1,
            random_movement=True,
            minimum_pixels=10,
            maximum_pixels=10,
            manual_move_threshold_pixels=20,
            manual_idle_seconds=0.5,
        )
        events: list[str] = []
        stop = threading.Event()
        timer = threading.Timer(0.2, stop.set)
        timer.start()
        try:
            MouseMover(backend, random.Random(4)).run(
                settings,
                stop,
                lambda kind, value: events.append(kind),
            )
        finally:
            timer.cancel()

        self.assertIn("manual_started", events)

    def test_pre_cancelled_run_does_not_move(self) -> None:
        backend = FakeBackend()
        stop = threading.Event()
        stop.set()
        MouseMover(backend).run(MovementSettings(1, 10), stop)
        self.assertEqual(backend.moves, [])


if __name__ == "__main__":
    unittest.main()
