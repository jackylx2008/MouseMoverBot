"""Native mouse backends selected in one platform boundary."""

from __future__ import annotations

import ctypes
import platform
from typing import Protocol


class MouseBackend(Protocol):
    def position(self) -> tuple[float, float]:
        ...

    def move_to(self, x: float, y: float) -> None:
        ...


class WindowsMouseBackend:
    """Mouse access through the Win32 API, available without pywin32."""

    def __init__(self) -> None:
        if platform.system() != "Windows":
            raise RuntimeError("Windows 鼠标后端只能在 Windows 上使用")
        self._user32 = ctypes.windll.user32  # type: ignore[attr-defined]

    def position(self) -> tuple[float, float]:
        point = _Point()
        if not self._user32.GetCursorPos(ctypes.byref(point)):
            raise OSError("Windows 无法读取鼠标位置")
        return float(point.x), float(point.y)

    def move_to(self, x: float, y: float) -> None:
        if not self._user32.SetCursorPos(round(x), round(y)):
            raise OSError("Windows 无法移动鼠标")


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MacOSMouseBackend:
    """Mouse access through macOS Quartz."""

    def __init__(self) -> None:
        if platform.system() != "Darwin":
            raise RuntimeError("macOS 鼠标后端只能在 macOS 上使用")
        try:
            import Quartz
        except ImportError as exc:
            raise RuntimeError(
                "缺少 macOS Quartz 支持，请执行 python -m pip install -r requirements.txt"
            ) from exc
        self._quartz = Quartz
        if hasattr(Quartz, "CGPreflightPostEventAccess") and not Quartz.CGPreflightPostEventAccess():
            raise RuntimeError(
                "macOS 尚未授权辅助功能。请在“系统设置 > 隐私与安全性 > 辅助功能”中允许当前终端或应用。"
            )

    def position(self) -> tuple[float, float]:
        event = self._quartz.CGEventCreate(None)
        point = self._quartz.CGEventGetLocation(event)
        return float(point.x), float(point.y)

    def move_to(self, x: float, y: float) -> None:
        self._quartz.CGWarpMouseCursorPosition((x, y))
        self._quartz.CGAssociateMouseAndMouseCursorPosition(True)


def create_mouse_backend(system: str | None = None) -> MouseBackend:
    """Return the supported native backend for the current OS."""
    platform_name = system or platform.system()
    if platform_name == "Windows":
        return WindowsMouseBackend()
    if platform_name == "Darwin":
        return MacOSMouseBackend()
    raise RuntimeError(f"当前系统不受支持: {platform_name}（仅支持 Windows 11 和 macOS）")
