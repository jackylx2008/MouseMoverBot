"""Application bootstrap and command-line validation entry."""

from __future__ import annotations

import argparse
import ctypes
import platform
import queue
import sys
from pathlib import Path

from mousemover.config_loader import load_config
from mousemover.context import AppContext
from mousemover.flows.movement_flow import FlowEvent, MovementFlow
from mousemover.logging_config import configure_utf8_stdio, get_logger, setup_logger
from mousemover.modules.mouse_backend import create_mouse_backend
from mousemover.modules.movement import MouseMover


PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows 11 / macOS 鼠标移动工具")
    parser.add_argument("--config-file", type=Path, default=PROJECT_ROOT / "config.yaml")
    parser.add_argument("--check", action="store_true", help="检查配置与平台后端后退出")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_utf8_stdio()
    try:
        config_file = args.config_file.expanduser().resolve()
        config = load_config(config_file, PROJECT_ROOT / "common.env")
        setup_logger(config.get("app", {}).get("log_level", "INFO"))
        logger = get_logger(__name__)
        context = AppContext(PROJECT_ROOT, config_file, config)
        backend = create_mouse_backend()
        if args.check:
            position = backend.position()
            logger.info("配置有效；%s 鼠标后端可用；当前位置=(%.0f, %.0f)", platform.system(), *position)
            return 0
        _set_windows_app_id()
        return run_gui(context, backend)
    except Exception as exc:
        print(f"Mouse Mover 启动失败：{exc}", file=sys.stderr)
        return 1


def run_gui(context: AppContext, backend: object) -> int:
    import tkinter as tk

    from mousemover.gui import MouseMoverWindow

    root = tk.Tk()
    events: queue.Queue[FlowEvent] = queue.Queue()
    flow = MovementFlow(MouseMover(backend), events)  # type: ignore[arg-type]
    MouseMoverWindow(root, flow, events, context.config, context.resource_dir)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        flow.cancel()
        root.destroy()
        return 130
    return 0


def _set_windows_app_id() -> None:
    if platform.system() == "Windows":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            "MouseMover.CrossPlatform.2"
        )
