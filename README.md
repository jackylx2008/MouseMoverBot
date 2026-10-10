# Mouse Mover

Mouse Mover 是一个适用于 Windows 11 和 macOS 的桌面鼠标移动工具。它会按设定间隔把指针移动少量像素再移回，用于避免空闲期间触发屏幕保护或自动锁定。

主要功能：

- 固定或随机移动距离；
- 固定或随机移动间隔；
- 按时、分、秒定时停止；
- 可随时安全取消，等待会立即响应停止信号；
- 实时状态、耗时和界面日志；
- Windows 使用系统 Win32 API，macOS 使用 Quartz API；
- 后台线程不直接操作 GUI 控件。

> 请遵守所在组织的设备管理和信息安全规定。本工具不应被用于规避强制安全策略。

## 支持环境

- Windows 11，Python 3.10 或更新版本；
- macOS，Python 3.10 或更新版本；
- Python 必须包含 Tkinter。Python.org 的 Windows/macOS 安装包通常已经包含它。

Linux 不是当前验收目标，程序会明确报告不支持，而不会静默调用错误的平台实现。

## 当前项目状态

当前版本为 `2.0.0`，跨平台重构已经完成。2026-10-09 在 macOS 上完成了以下实际验证：

- Python 3.14.8、Tk 9.1 窗口启动；
- Quartz 后端和辅助功能权限检查；
- 鼠标短距离移动并复位；
- 开始、取消、定时和线程事件的自动化测试；
- 隐藏窗口构建、静态检查、依赖检查和 wheel 构建。

Windows 11 的 Win32 后端已有自动化模拟测试，但仍需要在真实 Windows 11 设备上完成 GUI、系统缩放、多显示器和打包产物验收。详细进度见 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。

## 安装

项目虚拟环境不能在 Windows 和 macOS 间同步复用；请在每台机器上分别创建。

### Windows 11（PowerShell）

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows 鼠标控制仅使用 Python 标准库，不再依赖 `pywin32`。

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS 首次运行前，请在“系统设置 > 隐私与安全性 > 辅助功能”中允许启动程序的终端、Python 或打包后的应用控制电脑。没有权限时，程序会给出明确错误。

如果 Homebrew Python 报错 `No module named '_tkinter'`，请安装与 Python 次版本一致的 Tk 组件，然后重新创建虚拟环境。例如 Python 3.14：

```bash
brew install python-tk@3.14
```

仓库同时忽略 `.venv/` 和历史环境目录 `venv/`。建议后续统一使用 `.venv/`。

## 运行

从项目根目录执行：

```bash
python mouse_mover.py
```

如果沿用本仓库当前的 `venv/` 环境，可直接执行：

```bash
./venv/bin/python mouse_mover.py
```

先检查配置、操作系统后端和权限，但不打开 GUI、不移动鼠标：

```bash
python mouse_mover.py --check
```

使用其他配置文件：

```bash
python mouse_mover.py --config-file path/to/config.yaml
```

点击“开始”后，设置区保持可见，底部会显示运行状态、当前阶段和实际耗时；“停止”或“取消任务”都采用同一安全取消流程。

### macOS 与 VS Code

如果 VS Code Code Runner 提示执行 `python -m pip install -r requirements.txt`，通常表示它调用了系统 Python，而不是项目虚拟环境。优先在终端使用项目解释器：

```bash
./venv/bin/python mouse_mover.py --check
./venv/bin/python mouse_mover.py
```

Python 扩展的 “Run Python File” 与 Code Runner 使用不同的解释器配置；仅执行 “Python: Select Interpreter” 不一定会改变 Code Runner。完整的解释器选择、`.vscode/settings.json` 示例和排错命令见 [`docs/MACOS_VSCODE_SETUP.md`](docs/MACOS_VSCODE_SETUP.md)。`.vscode/` 是本机配置，已被 Git 忽略。

## 配置

公共默认值位于根目录 [`config.yaml`](config.yaml)。本机差异可写入不提交的 `common.env`：

```bash
cp common.env.example common.env
```

支持的常用覆盖变量：

```dotenv
LOG_LEVEL=INFO
MOUSE_MOVER_DELAY=1.0
MOUSE_MOVER_OFFSET=20
```

`common.env` 不覆盖进程中已经存在的环境变量。配置文件支持 `${NAME:-default}` 形式的变量展开。窗口内修改只影响本次运行，不会写回配置文件。

运行日志保存在 `logs/mouse_mover.log`，单文件最大 10 MB，保留 5 份备份。界面的“清空界面日志”不会删除磁盘日志。

## 测试

安装开发依赖及项目可编辑包后运行测试：

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m unittest discover -s tests -v
python -m flake8 mouse_mover.py logging_config.py src tests
python -m compileall -q mouse_mover.py logging_config.py src tests
```

GUI 测试只构建隐藏窗口；在没有图形会话的 CI 中会自动跳过，不会弹出长期驻留窗口。

## 打包

打包工具与运行依赖分离：

```bash
python -m pip install -r requirements-build.txt
```

Windows PowerShell：

```powershell
pyinstaller --clean --onefile --windowed --name MouseMover `
  --add-data "config.yaml;." `
  --add-data "mousemover/resource;mousemover/resource" `
  --icon "mousemover/resource/icon.ico" mouse_mover.py
```

macOS：

```bash
pyinstaller --clean --windowed --name MouseMover \
  --add-data "config.yaml:." \
  --add-data "mousemover/resource:mousemover/resource" mouse_mover.py
```

打包产物需要在对应操作系统上分别构建和验收，不能用一个平台的产物替代另一个平台。

## 项目结构

```text
mouse_mover.py                 根目录 GUI 入口
config.yaml                    公共配置
common.env.example             本机配置示例
logging_config.py              统一控制台与滚动文件日志
src/mousemover/modules/        配置无关的鼠标基础能力
src/mousemover/flows/          后台任务编排与线程事件
src/mousemover/gui.py          Tkinter 界面
tests/                         单元测试和隐藏窗口测试
docs/                          项目规范与说明
```

## License

本项目使用 [MIT License](LICENSE.md)。
