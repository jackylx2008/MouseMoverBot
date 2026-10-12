from __future__ import annotations

import queue
import unittest
from pathlib import Path

try:
    import tkinter as tk
    from mousemover.gui import MouseMoverWindow, _window_geometry
except (ImportError, ModuleNotFoundError):
    tk = None  # type: ignore[assignment]
    MouseMoverWindow = None  # type: ignore[assignment,misc]
    _window_geometry = None  # type: ignore[assignment,misc]

from mousemover.flows.movement_flow import FlowEvent


class FakeFlow:
    is_running = True

    def __init__(self) -> None:
        self.cancelled = False

    def start(self, settings: object) -> None:
        return None

    def cancel(self) -> None:
        self.cancelled = True


class FakeHotkeyManager:
    shortcut = ""

    def configure(self, shortcut: str) -> str:
        self.shortcut = shortcut
        return "<ctrl>+<alt>+s"

    def stop(self) -> None:
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
            flow = FakeFlow()
            window = MouseMoverWindow(  # type: ignore[misc]
                root,
                flow,  # type: ignore[arg-type]
                FakeHotkeyManager(),  # type: ignore[arg-type]
                queue.Queue(),
                {"mouse_movement": {}, "gui": {}},
                Path("missing-resource-directory"),
            )
            self.assertEqual(window.status_var.get(), "就绪")
            self.assertEqual(window.movement_duration_var.get(), "0.4")
            self.assertEqual(window.hotkey_status_var.get(), "已启用")
            first_log_line = window.log_text.get("1.0", "2.0").strip()
            self.assertRegex(
                first_log_line,
                r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] 全局停止快捷键已启用：",
            )
            window._active_duration_seconds = 10
            window._handle_event(FlowEvent("started"))
            window._handle_event(FlowEvent("tick", (4.25, 5.75)))
            self.assertEqual(str(window.progress.cget("mode")), "determinate")
            self.assertEqual(str(window.progress.cget("style")), "Green.Horizontal.TProgressbar")
            self.assertAlmostEqual(float(window.progress.cget("value")), 4.25)
            window._handle_event(
                FlowEvent(
                    "movement_area",
                    {"x": 100, "y": 100, "width": 400, "height": 300, "anchor": (300, 250)},
                )
            )
            root.update_idletasks()
            self.assertEqual(len(window.area_overlay._windows), 4)
            self.assertIsNotNone(window.area_overlay._after_id)
            window._handle_event(FlowEvent("manual_started", {"position": (200, 300)}))
            self.assertEqual(str(window.progress.cget("style")), "Yellow.Horizontal.TProgressbar")
            self.assertEqual(float(window.progress.cget("value")), 100)
            self.assertIsNone(window.area_overlay._after_id)
            window._handle_event(FlowEvent("manual_ended", {"position": (220, 320)}))
            self.assertEqual(str(window.progress.cget("style")), "Green.Horizontal.TProgressbar")
            window._handle_event(FlowEvent("hotkey_stop"))
            self.assertTrue(flow.cancelled)
            window._handle_event(FlowEvent("finished", "已取消"))
            self.assertEqual(str(window.progress.cget("style")), "Red.Horizontal.TProgressbar")
            self.assertEqual(float(window.progress.cget("value")), 100)
        finally:
            window._closing = True
            root.destroy()

    @unittest.skipIf(_window_geometry is None, "Tkinter 不可用")
    def test_overlay_geometry_supports_negative_coordinates(self) -> None:
        self.assertEqual(_window_geometry(400, 4, -200, 100), "400x4-200+100")  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
