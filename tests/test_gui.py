from __future__ import annotations

import queue
import unittest
from pathlib import Path

try:
    import tkinter as tk
    from mousemover.gui import MouseMoverWindow
except (ImportError, ModuleNotFoundError):
    tk = None  # type: ignore[assignment]
    MouseMoverWindow = None  # type: ignore[assignment,misc]


class FakeFlow:
    is_running = False

    def start(self, settings: object) -> None:
        return None

    def cancel(self) -> None:
        return None


class GuiBuildTests(unittest.TestCase):
    @unittest.skipIf(tk is None, "当前 Python 未安装 Tkinter")
    def test_hidden_window_builds(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"没有可用的图形会话: {exc}")
        root.withdraw()
        try:
            window = MouseMoverWindow(  # type: ignore[misc]
                root,
                FakeFlow(),  # type: ignore[arg-type]
                queue.Queue(),
                {"mouse_movement": {}, "gui": {}},
                Path("missing-resource-directory"),
            )
            self.assertEqual(window.status_var.get(), "就绪")
        finally:
            window._closing = True
            root.destroy()


if __name__ == "__main__":
    unittest.main()
