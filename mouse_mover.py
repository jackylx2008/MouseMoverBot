"""Mouse Mover 跨平台桌面工具

用途：
  在 Windows 11 或 macOS 上按设定间隔轻微移动鼠标，并可在指定时长后停止。

配置文件：
  默认读取项目根目录的 config.yaml；common.env 可覆盖本机运行参数且不会入库。

可选参数：
  --config-file  指定 YAML 配置文件，默认是项目根目录 config.yaml。
  --check        只检查配置和当前平台后端，不打开窗口或移动鼠标。

示例：
  python mouse_mover.py
  python mouse_mover.py --check

输出：
  界面显示运行状态，运行日志写入项目根目录 logs/mouse_mover.log。
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mousemover.app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
