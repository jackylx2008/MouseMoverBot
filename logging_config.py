"""项目统一日志配置的稳定根模块入口。"""

from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mousemover.logging_config import configure_utf8_stdio, get_logger, setup_logger

__all__ = ["configure_utf8_stdio", "get_logger", "setup_logger"]
