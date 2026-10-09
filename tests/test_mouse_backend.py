from __future__ import annotations

import ctypes
import unittest
from unittest.mock import patch

from mousemover.modules.mouse_backend import WindowsMouseBackend, create_mouse_backend


class FakeUser32:
    def __init__(self) -> None:
        self.target: tuple[int, int] | None = None

    @staticmethod
    def GetCursorPos(pointer: object) -> int:
        point = pointer._obj  # type: ignore[attr-defined]
        point.x = 120
        point.y = 240
        return 1

    def SetCursorPos(self, x: int, y: int) -> int:
        self.target = (x, y)
        return 1


class MouseBackendTests(unittest.TestCase):
    def test_windows_backend_uses_native_coordinates(self) -> None:
        user32 = FakeUser32()
        fake_windll = type("FakeWindll", (), {"user32": user32})()
        with patch("mousemover.modules.mouse_backend.platform.system", return_value="Windows"):
            with patch.object(ctypes, "windll", fake_windll, create=True):
                backend = WindowsMouseBackend()
                self.assertEqual(backend.position(), (120.0, 240.0))
                backend.move_to(135.4, 260.6)
        self.assertEqual(user32.target, (135, 261))

    def test_unsupported_platform_is_explicit(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "不受支持"):
            create_mouse_backend("Linux")


if __name__ == "__main__":
    unittest.main()
