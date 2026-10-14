"""Project-wide console and rotating file logging."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_NAME = "mouse_mover.log"


def setup_logger(
    log_level: int | str = logging.INFO,
    log_file: str | Path | None = None,
) -> logging.Logger:
    """Configure console output and a UTF-8 rotating log file."""
    level = _coerce_log_level(log_level)
    target = Path(log_file) if log_file else _default_log_file()
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    file_handler = RotatingFileHandler(
        target,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    return root_logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger that uses the project-level handlers."""
    return logging.getLogger(name)


def configure_utf8_stdio() -> None:
    """Use UTF-8 on terminals that support stream reconfiguration."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _coerce_log_level(log_level: int | str) -> int:
    if isinstance(log_level, int):
        return log_level
    level = logging.getLevelName(log_level.upper())
    if not isinstance(level, int):
        raise ValueError(f"未知日志级别: {log_level}")
    return level


def _default_log_file(
    *,
    frozen: bool | None = None,
    platform_name: str | None = None,
    home: Path | None = None,
    local_app_data: str | None = None,
) -> Path:
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if not is_frozen:
        return PROJECT_ROOT / "logs" / LOG_FILE_NAME

    active_platform = sys.platform if platform_name is None else platform_name
    user_home = Path.home() if home is None else home
    if active_platform == "darwin":
        return user_home / "Library" / "Logs" / "MouseMover" / LOG_FILE_NAME
    if active_platform == "win32":
        app_data = local_app_data if local_app_data is not None else os.environ.get("LOCALAPPDATA")
        base = Path(app_data) if app_data else user_home / "AppData" / "Local"
        return base / "MouseMover" / "logs" / LOG_FILE_NAME
    return user_home / ".mousemover" / "logs" / LOG_FILE_NAME
