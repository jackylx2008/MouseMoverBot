"""Load project configuration and machine-local environment overrides."""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path
from typing import Any, Mapping

import yaml


ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def load_config(config_file: Path, env_file: Path | None = None) -> dict[str, Any]:
    """Load UTF-8 YAML after applying common.env and ${NAME:-default}."""
    if env_file is not None:
        load_env_file(env_file)
    raw = config_file.read_text(encoding="utf-8")
    expanded = ENV_PATTERN.sub(_replace_env, raw)
    data = yaml.safe_load(expanded)
    if not isinstance(data, dict):
        raise ValueError(f"配置文件必须包含 YAML 映射: {config_file}")
    return data


def load_env_file(path: Path, environ: dict[str, str] | None = None) -> None:
    """Read a simple dotenv file without replacing existing values."""
    if not path.exists():
        return
    target = os.environ if environ is None else environ
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number} 缺少 '='")
        name, value = line.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"{path}:{line_number} 环境变量名为空")
        target.setdefault(name, value.strip().strip('"').strip("'"))


def select_cloudstation_root(
    environ: Mapping[str, str] | None = None,
    system: str | None = None,
) -> Path | None:
    """Resolve the shared root for the active operating system."""
    values = os.environ if environ is None else environ
    explicit = values.get("CLOUDSTATION_ROOT")
    if explicit:
        return Path(explicit).expanduser()
    platform_name = (system or platform.system()).upper()
    suffix = {"WINDOWS": "WINDOWS", "DARWIN": "MACOS", "LINUX": "LINUX"}.get(platform_name)
    value = values.get(f"CLOUDSTATION_ROOT_{suffix}") if suffix else None
    return Path(value).expanduser() if value else None


def _replace_env(match: re.Match[str]) -> str:
    name, default = match.group(1), match.group(2)
    value = os.environ.get(name, default)
    if value is None:
        raise ValueError(f"缺少环境变量: {name}")
    return value
