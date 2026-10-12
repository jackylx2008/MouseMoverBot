from __future__ import annotations

import logging
import re
import tempfile
import unittest
from pathlib import Path

from mousemover.logging_config import setup_logger


class LoggingConfigTests(unittest.TestCase):
    def test_file_log_uses_timestamp(self) -> None:
        root_logger = logging.getLogger()
        previous_handlers = root_logger.handlers[:]
        previous_level = root_logger.level
        with tempfile.TemporaryDirectory() as directory:
            log_file = Path(directory) / "timestamp.log"
            try:
                setup_logger("INFO", log_file)
                logging.getLogger("timestamp-test").info("测试消息")
                for handler in root_logger.handlers:
                    handler.flush()
                line = log_file.read_text(encoding="utf-8").strip()
            finally:
                for handler in root_logger.handlers:
                    handler.close()
                root_logger.handlers = previous_handlers
                root_logger.setLevel(previous_level)

        self.assertTrue(
            re.fullmatch(
                r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] "
                r"INFO timestamp-test - 测试消息",
                line,
            )
        )
