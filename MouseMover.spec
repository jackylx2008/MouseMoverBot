# -*- mode: python ; coding: utf-8 -*-
"""Build the macOS app with bundled resources and the project version."""

import re
from pathlib import Path


project_root = Path(SPECPATH).resolve()
metadata = (project_root / "pyproject.toml").read_text(encoding="utf-8")
version_match = re.search(r'^version\s*=\s*"([^"]+)"', metadata, re.MULTILINE)
if version_match is None:
    raise RuntimeError("pyproject.toml 中缺少项目版本")
version = version_match.group(1)
icon = str(project_root / "mousemover" / "resource" / "MouseMover.icns")

a = Analysis(
    [str(project_root / "mouse_mover.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (str(project_root / "config.yaml"), "."),
        (str(project_root / "mousemover" / "resource"), "mousemover/resource"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MouseMover",
    console=False,
    icon=icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="MouseMover",
)
app = BUNDLE(
    coll,
    name="MouseMover.app",
    icon=icon,
    bundle_identifier="com.jackylx.mousemover",
    info_plist={
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
    },
)
