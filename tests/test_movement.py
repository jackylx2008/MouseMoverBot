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


class StopAfterTwoWaits:
    def __init__(self) -> None:
        self.calls = 0

    def is_set(self) -> bool:
        return self.calls >= 2

    def wait(self, timeout: float) -> bool:
        self.calls += 1
        return self.calls >= 2


class MovementTests(unittest.TestCase):
    def test_moves_away_then_returns_to_origin(self) -> None:
        backend = FakeBackend()
        mover = MouseMover(backend, random.Random(4))
        mover.run(MovementSettings(delay_seconds=0.1, offset_pixels=10), StopAfterTwoWaits())  # type: ignore[arg-type]
        self.assertEqual(len(backend.moves), 2)
        self.assertEqual(backend.moves[-1], (100.0, 100.0))

    def test_invalid_delay_is_rejected(self) -> None:
        settings = MovementSettings(delay_seconds=0, offset_pixels=10)
        with self.assertRaisesRegex(ValueError, "移动间隔"):
            settings.validate()

    def test_pre_cancelled_run_does_not_move(self) -> None:
        backend = FakeBackend()
        stop = threading.Event()
        stop.set()
        MouseMover(backend).run(MovementSettings(1, 10), stop)
        self.assertEqual(backend.moves, [])


if __name__ == "__main__":
    unittest.main()
