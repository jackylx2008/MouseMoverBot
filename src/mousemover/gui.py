"""Responsive Tkinter user interface."""

from __future__ import annotations

import datetime
import queue
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from mousemover.flows.movement_flow import FlowEvent, MovementFlow
from mousemover.modules.movement import MovementSettings


class MouseMoverWindow:
    def __init__(
        self,
        root: tk.Tk,
        flow: MovementFlow,
        events: queue.Queue[FlowEvent],
        config: dict[str, Any],
        resource_dir: Path,
    ) -> None:
        self.root = root
        self.flow = flow
        self.events = events
        self.config = config
        self._closing = False
        self._build_window(resource_dir)
        self._build_content()
        self._load_defaults()
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
        self.random_movement_var = tk.BooleanVar()
        self.min_pixels_var = tk.StringVar()
        self.max_pixels_var = tk.StringVar()
        self.random_delay_var = tk.BooleanVar()
        self.min_delay_var = tk.StringVar()
        self.max_delay_var = tk.StringVar()
        self.timer_var = tk.BooleanVar()
        self.hours_var = tk.StringVar(value="0")
        self.minutes_var = tk.StringVar(value="0")
        self.seconds_var = tk.StringVar(value="0")

        ttk.Label(parent, text="基础间隔（秒）").grid(row=0, column=0, sticky="w")
        self._entry(parent, self.delay_var, 0, 1)
        ttk.Label(parent, text="基础距离（像素）").grid(row=0, column=2, sticky="w", padx=(16, 0))
        self._entry(parent, self.offset_var, 0, 3)

        ttk.Checkbutton(parent, text="随机移动距离", variable=self.random_movement_var).grid(
            row=1, column=0, sticky="w", pady=(10, 0)
        )
        self._entry(parent, self.min_pixels_var, 1, 1)
        ttk.Label(parent, text="至").grid(row=1, column=2)
        self._entry(parent, self.max_pixels_var, 1, 3)

        ttk.Checkbutton(parent, text="随机附加延迟", variable=self.random_delay_var).grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        self._entry(parent, self.min_delay_var, 2, 1)
        ttk.Label(parent, text="至（秒）").grid(row=2, column=2)
        self._entry(parent, self.max_delay_var, 2, 3)

        ttk.Checkbutton(parent, text="定时停止", variable=self.timer_var).grid(
            row=3, column=0, sticky="w", pady=(10, 0)
        )
        timer = ttk.Frame(parent)
        timer.grid(row=3, column=1, columnspan=3, sticky="w", pady=(10, 0))
        for label, variable in (("时", self.hours_var), ("分", self.minutes_var), ("秒", self.seconds_var)):
            ttk.Spinbox(timer, from_=0, to=99 if label == "时" else 59, width=5, textvariable=variable).pack(
                side="left"
            )
            ttk.Label(timer, text=label).pack(side="left", padx=(2, 8))

        buttons = ttk.Frame(parent)
        buttons.grid(row=4, column=0, columnspan=4, sticky="e", pady=(14, 0))
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
        self.random_movement_var.set(bool(random_movement.get("enabled", False)))
        self.min_pixels_var.set(str(random_movement.get("minimum_pixels", 5)))
        self.max_pixels_var.set(str(random_movement.get("maximum_pixels", 40)))
        self.random_delay_var.set(bool(random_delay.get("enabled", False)))
        self.min_delay_var.set(str(random_delay.get("minimum_seconds", 0)))
        self.max_delay_var.set(str(random_delay.get("maximum_seconds", 10)))

    def _settings(self) -> MovementSettings:
        duration = None
        if self.timer_var.get():
            duration = int(self.hours_var.get()) * 3600 + int(self.minutes_var.get()) * 60 + int(
                self.seconds_var.get()
            )
        return MovementSettings(
            delay_seconds=float(self.delay_var.get()),
            offset_pixels=int(self.offset_var.get()),
            random_movement=self.random_movement_var.get(),
            minimum_pixels=int(self.min_pixels_var.get()),
            maximum_pixels=int(self.max_pixels_var.get()),
            random_delay=self.random_delay_var.get(),
            minimum_delay_seconds=float(self.min_delay_var.get()),
            maximum_delay_seconds=float(self.max_delay_var.get()),
            duration_seconds=duration,
        )

    def _start(self) -> None:
        try:
            self.flow.start(self._settings())
        except (TypeError, ValueError, RuntimeError) as exc:
            messagebox.showerror("无法启动", str(exc), parent=self.root)

    def _cancel(self) -> None:
        self.flow.cancel()

    def _set_running(self, running: bool) -> None:
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.cancel_button.configure(state="normal" if running else "disabled")
        if running:
            self.progress.start(12)
        else:
            self.progress.stop()

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
            self.elapsed_var.set(_format_seconds(elapsed))
            self.current_var.set(
                "持续运行" if remaining is None else f"剩余 {_format_seconds(remaining)}"
            )
        elif event.kind == "log":
            self._append_log(str(event.value))
        elif event.kind == "finished":
            self.status_var.set(str(event.value))
            self.current_var.set("等待启动")
            self._set_running(False)
        elif event.kind == "failed":
            self.status_var.set("失败")
            self.current_var.set("等待启动")
            self._set_running(False)
            self._append_log(f"错误：{event.value}")
            messagebox.showerror("任务失败", str(event.value), parent=self.root)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
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
        self.flow.cancel()
        self.root.destroy()


def _format_seconds(seconds: int) -> str:
    return str(datetime.timedelta(seconds=max(0, seconds)))
