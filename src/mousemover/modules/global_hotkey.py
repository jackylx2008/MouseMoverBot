"""Cross-platform global hotkey registration."""

from __future__ import annotations

import platform
import re
import threading
from collections.abc import Callable

from pynput import keyboard


_ALIASES = {
    "control": "ctrl",
    "ctrl": "ctrl",
    "option": "alt",
    "opt": "alt",
    "alt": "alt",
    "command": "cmd",
    "cmd": "cmd",
    "super": "cmd",
    "shift": "shift",
}
_MODIFIER_ORDER = ("ctrl", "alt", "shift", "cmd")
_NAMED_KEYS = {
    "space",
    "tab",
    "enter",
    "esc",
    "home",
    "end",
    "page_up",
    "page_down",
    "up",
    "down",
    "left",
    "right",
}


def canonicalize_hotkey(value: str) -> str:
    """Convert a user-facing shortcut into pynput GlobalHotKeys syntax."""
    raw_parts = [part.strip().lower() for part in value.split("+") if part.strip()]
    parts = [_ALIASES.get(part, part) for part in raw_parts]
    if len(parts) != len(set(parts)):
        raise ValueError("快捷键不能包含重复按键")

    modifiers = [part for part in _MODIFIER_ORDER if part in parts]
    keys = [part for part in parts if part not in _MODIFIER_ORDER]
    if not modifiers:
        raise ValueError("全局快捷键至少需要一个修饰键")
    if len(keys) != 1:
        raise ValueError("全局快捷键必须包含一个普通按键")

    key = keys[0]
    if len(key) == 1 and key.isalnum():
        key_token = key
    elif key in _NAMED_KEYS or re.fullmatch(r"f(?:[1-9]|1[0-9]|2[0-4])", key):
        key_token = f"<{key}>"
    else:
        raise ValueError(f"不支持的快捷键按键: {key}")

    return "+".join([*(f"<{part}>" for part in modifiers), key_token])


class GlobalHotkeyManager:
    """Own one process-wide hotkey listener that can be reconfigured."""

    def __init__(self, on_stop: Callable[[], None]) -> None:
        self._on_stop = on_stop
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()
        self._shortcut = ""

    @property
    def shortcut(self) -> str:
        return self._shortcut

    def configure(self, value: str) -> str:
        canonical = canonicalize_hotkey(value)
        _check_macos_input_permission()
        with self._lock:
            self._stop_locked()
            hotkey = keyboard.HotKey(keyboard.HotKey.parse(canonical), self._on_stop)
            listener: keyboard.Listener

            def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
                if key is not None:
                    hotkey.press(listener.canonical(key))

            def on_release(key: keyboard.Key | keyboard.KeyCode | None) -> None:
                if key is not None:
                    hotkey.release(listener.canonical(key))

            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            listener.daemon = True
            listener.start()
            listener.wait()
            self._listener = listener
            self._shortcut = value.strip()
        return canonical

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()
            self._shortcut = ""

    def _stop_locked(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener.join(timeout=0.5)
        self._listener = None


def _check_macos_input_permission() -> None:
    if platform.system() != "Darwin":
        return
    try:
        import Quartz
    except ImportError as exc:
        raise RuntimeError("缺少 macOS Quartz 支持") from exc
    if hasattr(Quartz, "CGPreflightListenEventAccess") and not Quartz.CGPreflightListenEventAccess():
        raise RuntimeError(
            "macOS 尚未授权全局键盘监听。请在“系统设置 > 隐私与安全性”中的“输入监控”或“辅助功能”中允许当前应用。"
        )
