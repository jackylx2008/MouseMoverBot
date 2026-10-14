"""Responsive Tkinter user interface."""

from __future__ import annotations

import datetime
import math
import queue
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from mousemover.flows.movement_flow import FlowEvent, MovementFlow
from mousemover.modules.global_hotkey import GlobalHotkeyManager
from mousemover.modules.movement import MovementSettings


class FlashingRectangleOverlay:
    """Four non-interactive top-level windows forming a flashing red frame."""

    _BORDER_WIDTH = 4
    _FLASH_INTERVAL_MS = 500

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._windows: list[tk.Toplevel] = []
        self._after_id: str | None = None
        self._visible = False

    def show(self, area: dict[str, Any]) -> None:
        self.hide()
        if not self._windows:
            for _ in range(4):
                window = tk.Toplevel(self.root)
                window.overrideredirect(True)
                window.attributes("-topmost", True)
                window.configure(background="#ff2020")
                self._windows.append(window)

        x = round(float(area["x"]))
        y = round(float(area["y"]))
        width = max(self._BORDER_WIDTH * 2, round(float(area["width"])))
        height = max(self._BORDER_WIDTH * 2, round(float(area["height"])))
        geometries = _rectangle_border_geometries(
            x,
            y,
            width,
            height,
            self._BORDER_WIDTH,
        )
        for window, geometry in zip(self._windows, geometries, strict=True):
            window.geometry(_window_geometry(*geometry))

        self._visible = True
        self._set_windows_visible(True)
        self._after_id = self.root.after(self._FLASH_INTERVAL_MS, self._schedule_blink)

    def hide(self) -> None:
        self._visible = False
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self._set_windows_visible(False)

    def close(self) -> None:
        self.hide()
        for window in self._windows:
            window.destroy()
        self._windows.clear()

    def _schedule_blink(self) -> None:
        if not self._visible:
            return
        currently_visible = any(window.state() == "normal" for window in self._windows)
        self._set_windows_visible(not currently_visible)
        self._after_id = self.root.after(self._FLASH_INTERVAL_MS, self._schedule_blink)

    def _set_windows_visible(self, visible: bool) -> None:
        for window in self._windows:
            if visible:
                window.deiconify()
                window.lift()
            else:
                window.withdraw()


class MouseMoverWindow:
    def __init__(
        self,
        root: tk.Tk,
        flow: MovementFlow,
        hotkey_manager: GlobalHotkeyManager,
        events: queue.Queue[FlowEvent],
        config: dict[str, Any],
        resource_dir: Path,
    ) -> None:
        self.root = root
        self.flow = flow
        self.hotkey_manager = hotkey_manager
        self.events = events
        self.config = config
        self._closing = False
        self._active_duration_seconds: int | None = None
        self._stopped_by_hotkey = False
        self._manual_active = False
        self._last_elapsed_seconds = 0.0
        self._area_initialized = False
        self._build_window(resource_dir)
        self._build_content()
        self.area_overlay = FlashingRectangleOverlay(root)
        self._load_defaults()
        self._apply_stop_hotkey(show_error=False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_events)

    def _build_window(self, resource_dir: Path) -> None:
        gui = self.config.get("gui", {})
        self.root.title(str(gui.get("title", "Mouse Mover")))
        self.root.minsize(int(gui.get("minimum_width", 720)), int(gui.get("minimum_height", 600)))
        icon = resource_dir / "48x48.png"
        if icon.exists():
            try:
                self._icon = tk.PhotoImage(file=icon)
                self.root.iconphoto(True, self._icon)
            except tk.TclError:
                pass
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(
            "Green.Horizontal.TProgressbar",
            background="#2eaf5d",
            troughcolor="#d9d9d9",
        )
        style.configure(
            "Red.Horizontal.TProgressbar",
            background="#d83b3b",
            troughcolor="#d83b3b",
        )
        style.configure(
            "Yellow.Horizontal.TProgressbar",
            background="#f2c230",
            troughcolor="#f2c230",
        )

    def _build_content(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer = ttk.Frame(self.root, padding=12)
        outer.grid(sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        notebook = ttk.Notebook(outer)
        notebook.grid(row=0, column=0, sticky="ew")
        controls = ttk.Frame(notebook, padding=12)
        notebook.add(controls, text="鼠标移动")
        self._build_controls(controls)

        log_frame = ttk.LabelFrame(outer, text="实时日志", padding=8)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 8))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        ttk.Button(log_frame, text="清空界面日志", command=self._clear_log).grid(
            row=1, column=0, sticky="e", pady=(6, 0)
        )

        status = ttk.Frame(outer)
        status.grid(row=2, column=0, sticky="ew")
        status.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(status, mode="indeterminate")
        self.progress.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 6))
        self.status_var = tk.StringVar(value="就绪")
        self.current_var = tk.StringVar(value="等待启动")
        self.elapsed_var = tk.StringVar(value="00:00:00")
        ttk.Label(status, textvariable=self.status_var, width=12).grid(row=1, column=0, sticky="w")
        ttk.Label(status, textvariable=self.current_var).grid(row=1, column=1, sticky="w")
        ttk.Label(status, textvariable=self.elapsed_var).grid(row=1, column=2, padx=12)
        self.cancel_button = ttk.Button(status, text="取消任务", command=self._cancel, state="disabled")
        self.cancel_button.grid(row=1, column=3, sticky="e")

    def _build_controls(self, parent: ttk.Frame) -> None:
        for column in (1, 3):
            parent.columnconfigure(column, weight=1)
        self.delay_var = tk.StringVar()
        self.offset_var = tk.StringVar()
        self.movement_duration_var = tk.StringVar()
        self.random_movement_var = tk.BooleanVar()
        self.min_pixels_var = tk.StringVar()
        self.max_pixels_var = tk.StringVar()
        self.area_width_var = tk.StringVar()
        self.area_height_var = tk.StringVar()
        self.manual_threshold_var = tk.StringVar()
        self.manual_idle_var = tk.StringVar()
        self.random_delay_var = tk.BooleanVar()
        self.min_delay_var = tk.StringVar()
        self.max_delay_var = tk.StringVar()
        self.timer_var = tk.BooleanVar()
        self.stop_hotkey_var = tk.StringVar()
        self.hotkey_status_var = tk.StringVar(value="未启用")
        self.hours_var = tk.StringVar(value="0")
        self.minutes_var = tk.StringVar(value="0")
        self.seconds_var = tk.StringVar(value="0")

        ttk.Label(parent, text="基础间隔（秒）").grid(row=0, column=0, sticky="w")
        self._entry(parent, self.delay_var, 0, 1)
        ttk.Label(parent, text="基础距离（像素）").grid(row=0, column=2, sticky="w", padx=(16, 0))
        self._entry(parent, self.offset_var, 0, 3)

        ttk.Label(parent, text="单程移动耗时（秒）").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self._entry(parent, self.movement_duration_var, 1, 1)

        ttk.Checkbutton(parent, text="启用随机范围移动", variable=self.random_movement_var).grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        self._entry(parent, self.min_pixels_var, 2, 1)
        ttk.Label(parent, text="至").grid(row=2, column=2)
        self._entry(parent, self.max_pixels_var, 2, 3)

        ttk.Checkbutton(parent, text="随机附加延迟", variable=self.random_delay_var).grid(
            row=3, column=0, sticky="w", pady=(10, 0)
        )
        self._entry(parent, self.min_delay_var, 3, 1)
        ttk.Label(parent, text="至（秒）").grid(row=3, column=2)
        self._entry(parent, self.max_delay_var, 3, 3)

        ttk.Label(parent, text="随机范围宽度（像素）").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self._entry(parent, self.area_width_var, 4, 1)
        ttk.Label(parent, text="高度（像素）").grid(row=4, column=2, sticky="w", padx=(16, 0))
        self._entry(parent, self.area_height_var, 4, 3)

        ttk.Label(parent, text="人工移动阈值（像素）").grid(row=5, column=0, sticky="w", pady=(10, 0))
        self._entry(parent, self.manual_threshold_var, 5, 1)
        ttk.Label(parent, text="静止后恢复（秒）").grid(row=5, column=2, sticky="w", padx=(16, 0))
        self._entry(parent, self.manual_idle_var, 5, 3)

        ttk.Checkbutton(parent, text="定时停止", variable=self.timer_var).grid(
            row=6, column=0, sticky="w", pady=(10, 0)
        )
        timer = ttk.Frame(parent)
        timer.grid(row=6, column=1, columnspan=3, sticky="w", pady=(10, 0))
        for label, variable in (("时", self.hours_var), ("分", self.minutes_var), ("秒", self.seconds_var)):
            ttk.Spinbox(timer, from_=0, to=99 if label == "时" else 59, width=5, textvariable=variable).pack(
                side="left"
            )
            ttk.Label(timer, text=label).pack(side="left", padx=(2, 8))

        ttk.Label(parent, text="全局停止快捷键").grid(row=7, column=0, sticky="w", pady=(10, 0))
        self._entry(parent, self.stop_hotkey_var, 7, 1)
        ttk.Button(parent, text="应用快捷键", command=self._apply_stop_hotkey).grid(
            row=7, column=2, sticky="w", padx=(8, 0), pady=(10, 0)
        )
        ttk.Label(parent, textvariable=self.hotkey_status_var).grid(
            row=7, column=3, sticky="w", padx=(8, 0), pady=(10, 0)
        )

        buttons = ttk.Frame(parent)
        buttons.grid(row=8, column=0, columnspan=4, sticky="e", pady=(14, 0))
        self.start_button = ttk.Button(buttons, text="开始", command=self._start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="停止", command=self._cancel, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))

    @staticmethod
    def _entry(parent: ttk.Frame, variable: tk.StringVar, row: int, column: int) -> None:
        ttk.Entry(parent, textvariable=variable, width=12).grid(
            row=row, column=column, sticky="ew", padx=(8, 0), pady=(4, 0)
        )

    def _load_defaults(self) -> None:
        movement = self.config.get("mouse_movement", {})
        random_movement = movement.get("random_movement", {})
        random_delay = movement.get("random_delay", {})
        self.delay_var.set(str(movement.get("delay_seconds", 1.0)))
        self.offset_var.set(str(movement.get("offset_pixels", 20)))
        self.movement_duration_var.set(str(movement.get("movement_duration_seconds", 0.4)))
        self.random_movement_var.set(bool(random_movement.get("enabled", True)))
        self.min_pixels_var.set(str(random_movement.get("minimum_pixels", 5)))
        self.max_pixels_var.set(str(random_movement.get("maximum_pixels", 40)))
        self.area_width_var.set(str(random_movement.get("area_width", 800)))
        self.area_height_var.set(str(random_movement.get("area_height", 600)))
        self.manual_threshold_var.set(str(random_movement.get("manual_move_threshold_pixels", 60)))
        self.manual_idle_var.set(str(random_movement.get("manual_idle_seconds", 3)))
        self.random_delay_var.set(bool(random_delay.get("enabled", True)))
        self.min_delay_var.set(str(random_delay.get("minimum_seconds", 0)))
        self.max_delay_var.set(str(random_delay.get("maximum_seconds", 10)))
        self.stop_hotkey_var.set(str(self.config.get("hotkeys", {}).get("stop", "ctrl+option+s")))

    def _apply_stop_hotkey(self, show_error: bool = True) -> None:
        shortcut = self.stop_hotkey_var.get().strip()
        try:
            self.hotkey_manager.configure(shortcut)
            self.hotkey_status_var.set("已启用")
            self._append_log(f"全局停止快捷键已启用：{shortcut}")
        except (ValueError, RuntimeError) as exc:
            self.hotkey_status_var.set("不可用")
            self._append_log(f"快捷键错误：{exc}")
            if show_error:
                messagebox.showerror("快捷键不可用", str(exc), parent=self.root)

    def _settings(self) -> MovementSettings:
        duration = None
        if self.timer_var.get():
            duration = int(self.hours_var.get()) * 3600 + int(self.minutes_var.get()) * 60 + int(
                self.seconds_var.get()
            )
        return MovementSettings(
            delay_seconds=float(self.delay_var.get()),
            offset_pixels=int(self.offset_var.get()),
            movement_duration_seconds=float(self.movement_duration_var.get()),
            random_movement=self.random_movement_var.get(),
            minimum_pixels=int(self.min_pixels_var.get()),
            maximum_pixels=int(self.max_pixels_var.get()),
            random_delay=self.random_delay_var.get(),
            minimum_delay_seconds=float(self.min_delay_var.get()),
            maximum_delay_seconds=float(self.max_delay_var.get()),
            random_area_width=int(self.area_width_var.get()),
            random_area_height=int(self.area_height_var.get()),
            manual_move_threshold_pixels=int(self.manual_threshold_var.get()),
            manual_idle_seconds=float(self.manual_idle_var.get()),
            duration_seconds=duration,
        )

    def _start(self) -> None:
        try:
            settings = self._settings()
            settings.validate()
            self._active_duration_seconds = settings.duration_seconds
            self._stopped_by_hotkey = False
            self._manual_active = False
            self._last_elapsed_seconds = 0.0
            self._area_initialized = False
            self.area_overlay.hide()
            self.flow.start(settings)
        except (TypeError, ValueError, RuntimeError) as exc:
            messagebox.showerror("无法启动", str(exc), parent=self.root)

    def _cancel(self) -> None:
        self.flow.cancel()

    def _set_running(self, running: bool) -> None:
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.cancel_button.configure(state="normal" if running else "disabled")
        if running:
            if self._active_duration_seconds is None:
                self.progress.configure(
                    mode="indeterminate",
                    maximum=100,
                    value=0,
                    style="Horizontal.TProgressbar",
                )
                self.progress.start(12)
            else:
                self.progress.stop()
                self.progress.configure(
                    mode="determinate",
                    maximum=self._active_duration_seconds,
                    value=0,
                    style="Green.Horizontal.TProgressbar",
                )
        else:
            self.progress.stop()

    def _finish_progress(self, outcome: str) -> None:
        self.progress.stop()
        if self._stopped_by_hotkey:
            self.progress.configure(
                mode="determinate",
                maximum=100,
                value=100,
                style="Red.Horizontal.TProgressbar",
            )
        elif outcome == "完成" and self._active_duration_seconds is not None:
            self.progress.configure(
                mode="determinate",
                maximum=self._active_duration_seconds,
                value=self._active_duration_seconds,
                style="Green.Horizontal.TProgressbar",
            )
        else:
            self.progress.configure(
                mode="determinate",
                maximum=100,
                value=0,
                style="Horizontal.TProgressbar",
            )

    def _show_hotkey_stop_progress(self) -> None:
        self._stopped_by_hotkey = True
        self._manual_active = False
        self.progress.stop()
        self.progress.configure(
            mode="determinate",
            maximum=100,
            value=100,
            style="Red.Horizontal.TProgressbar",
        )

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        if not self._closing:
            self.root.after(100, self._drain_events)

    def _handle_event(self, event: FlowEvent) -> None:
        if event.kind == "started":
            self.status_var.set("运行")
            self.current_var.set("正在移动鼠标")
            self._set_running(True)
        elif event.kind == "status":
            self.status_var.set(str(event.value))
        elif event.kind == "tick":
            elapsed, remaining = event.value
            self._last_elapsed_seconds = elapsed
            self.elapsed_var.set(_format_seconds(math.floor(elapsed)))
            if not self._manual_active:
                self.current_var.set(
                    "持续运行" if remaining is None else f"剩余 {_format_seconds(math.ceil(remaining))}"
                )
                if self._active_duration_seconds is not None and not self._stopped_by_hotkey:
                    self.progress.configure(value=min(elapsed, self._active_duration_seconds))
        elif event.kind == "log":
            self._append_log(str(event.value))
        elif event.kind == "movement_area":
            self.area_overlay.show(event.value)
            anchor_x, anchor_y = event.value["anchor"]
            if self._area_initialized:
                self._append_log(
                    f"随机移动范围已更新：锚点 ({anchor_x:.0f}, {anchor_y:.0f})，"
                    f"{event.value['width']:.0f} × {event.value['height']:.0f} 像素"
                )
            else:
                self._area_initialized = True
                self._append_log(
                    f"随机移动范围已显示：锚点 ({anchor_x:.0f}, {anchor_y:.0f})，"
                    f"{event.value['width']:.0f} × {event.value['height']:.0f} 像素"
                )
        elif event.kind == "manual_started":
            self._manual_active = True
            self.status_var.set("人工操作")
            self.current_var.set("检测到人工移动，等待鼠标静止")
            self.progress.stop()
            self.progress.configure(
                mode="determinate",
                maximum=100,
                value=100,
                style="Yellow.Horizontal.TProgressbar",
            )
            self._append_log("检测到人工大幅移动，已暂停自动随机移动")
        elif event.kind == "manual_ended":
            self._manual_active = False
            self.status_var.set("运行")
            self.current_var.set("人工操作结束，正在从新锚点恢复")
            self._restore_running_progress()
            x, y = event.value["position"]
            self._append_log(f"人工移动结束，新锚点为 ({x:.0f}, {y:.0f})，恢复随机移动")
        elif event.kind == "hotkey_stop":
            if self.flow.is_running:
                self._append_log(f"已按下全局快捷键 {self.hotkey_manager.shortcut}，正在停止")
                self._show_hotkey_stop_progress()
                self.flow.cancel()
        elif event.kind == "finished":
            self.status_var.set(str(event.value))
            self.current_var.set("等待启动")
            self._set_running(False)
            self._finish_progress(str(event.value))
            self.area_overlay.hide()
        elif event.kind == "failed":
            self.status_var.set("失败")
            self.current_var.set("等待启动")
            self._set_running(False)
            self._finish_progress("失败")
            self.area_overlay.hide()
            self._append_log(f"错误：{event.value}")
            messagebox.showerror("任务失败", str(event.value), parent=self.root)

    def _restore_running_progress(self) -> None:
        if self._active_duration_seconds is None:
            self.progress.configure(
                mode="indeterminate",
                maximum=100,
                value=0,
                style="Horizontal.TProgressbar",
            )
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.configure(
                mode="determinate",
                maximum=self._active_duration_seconds,
                value=min(self._last_elapsed_seconds, self._active_duration_seconds),
                style="Green.Horizontal.TProgressbar",
            )

    def _append_log(self, message: str) -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 3000:
            self.log_text.delete("1.0", f"{line_count - 3000}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _on_close(self) -> None:
        if self.flow.is_running and not messagebox.askyesno(
            "退出", "任务正在运行。停止任务并退出吗？", parent=self.root
        ):
            return
        self._closing = True
        self.area_overlay.close()
        self.hotkey_manager.stop()
        self.flow.cancel()
        self.root.destroy()


def _format_seconds(seconds: int) -> str:
    return str(datetime.timedelta(seconds=max(0, seconds)))


def _window_geometry(width: int, height: int, x: int, y: int) -> str:
    return f"{width}x{height}{x:+d}{y:+d}"


def _rectangle_border_geometries(
    x: int,
    y: int,
    width: int,
    height: int,
    border: int,
) -> tuple[tuple[int, int, int, int], ...]:
    """Return four touching border segments without overlapping corners."""
    inner_height = max(1, height - (border * 2))
    return (
        (width, border, x, y),
        (width, border, x, y + height - border),
        (border, inner_height, x, y + border),
        (border, inner_height, x + width - border, y + border),
    )
