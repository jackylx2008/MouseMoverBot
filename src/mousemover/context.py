"""Application-wide paths and configuration context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AppContext:
    project_root: Path
    config_file: Path
    config: dict[str, Any]

    @property
    def resource_dir(self) -> Path:
        return self.project_root / "mousemover" / "resource"
