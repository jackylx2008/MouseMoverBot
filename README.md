# Mouse Mover

Mouse Mover 是一个适用于 Windows 11 和 macOS 的桌面鼠标移动工具。它会按设定间隔平滑移动指针，用于避免空闲期间触发屏幕保护或自动锁定。

主要功能：

- 连续平滑移动，支持配置单程移动耗时；
- 固定或随机移动距离；
- 随机模式以鼠标当前位置为锚点，在可配置的矩形范围内连续游走；
- 检测到人工大幅移动时自动暂停，鼠标静止一段时间后以人工停留点为新锚点恢复；
- 随机范围使用闪烁红框提示，人工操作期间使用满格黄色进度条提示；
- 固定或随机移动间隔；
- 按时、分、秒定时停止；
- 可配置全局停止快捷键，窗口失去焦点后仍可停止任务；
- 可随时安全取消，等待会立即响应停止信号；
- 实时状态、耗时和界面日志；
- 无限运行时显示滚动进度，定时运行时显示随时间增长的绿色进度；
- Windows 使用系统 Win32 API，macOS 使用 Quartz API；
- 后台线程不直接操作 GUI 控件。

> 请遵守所在组织的设备管理和信息安全规定。本工具不应被用于规避强制安全策略。

## 支持环境

- Windows 11，Python 3.10 或更新版本；
- macOS，Python 3.10 或更新版本；
- Python 必须包含 Tkinter。Python.org 的 Windows/macOS 安装包通常已经包含它。

Linux 不是当前验收目标，程序会明确报告不支持，而不会静默调用错误的平台实现。

## 当前项目状态

当前版本为 `2.0.0`，跨平台重构已经完成。2026-10-12 已确认应用在 macOS 上运行正常；此前完成的实机验证包括：

- Python 3.14.8、Tk 9.1 窗口启动；
- Quartz 后端和辅助功能权限检查；
- 鼠标短距离移动并复位；
- 60 FPS 缓入缓出连续移动；固定模式取消后平滑复位，随机模式停在当前点；
- 人工大幅移动触发暂停，静止后以新锚点重建随机范围并恢复；
- 开始、取消、定时和线程事件的自动化测试；
- 隐藏窗口构建、静态检查、依赖检查和 wheel 构建。

macOS 端当前结论为“实机验收通过”：应用可从项目虚拟环境启动，主窗口和鼠标移动功能运行正常；根目录 `MouseMover.app` 已完成构建、签名检查和双击启动验证。面向其他电脑分发前仍需使用 Apple Developer 证书签名并完成公证。

2026-10-14 在新 Mac mini（Apple Silicon）上使用 Python 3.13.16、Tk 9.0 和 `uv` 重新创建 `.venv/`，安装运行、测试及打包依赖；25 项测试通过。根目录 App 已重新构建为 2.0.0 并通过签名完整性检查。此电脑的辅助功能列表仍只授权了备份的旧 App，新 App 需要单独授权后才能控制鼠标。

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
uv venv --python python3 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt -r requirements-build.txt -e .
```

macOS 首次运行前，请在“系统设置 > 隐私与安全性 > 辅助功能”中允许实际启动程序的 VS Code、终端或打包后的 App 控制电脑。源码运行和双击 `.app` 使用不同的授权条目。

如果 Homebrew Python 报错 `No module named '_tkinter'`，请安装与 Python 次版本一致的 Tk 组件，然后重新创建虚拟环境。例如 Python 3.14：

```bash
brew install python-tk@3.14
```

`.gitignore` 排除了 `.venv/` 和历史环境目录 `venv/`。每台机器都应创建自己的 `.venv/`。

## 运行

从项目根目录执行：

```bash
python mouse_mover.py
```

不激活环境也可直接执行：

```bash
./.venv/bin/python mouse_mover.py
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
./.venv/bin/python mouse_mover.py --check
./.venv/bin/python mouse_mover.py
```

Python 扩展的 “Run Python File” 与 Code Runner 使用不同的解释器配置；仅执行 “Python: Select Interpreter” 不一定会改变 Code Runner。本机 `.vscode/settings.json` 将 Code Runner 指向 `.venv/bin/python`，并显式传入当前文件。请打开 `mouse_mover.py` 或兼容入口 `main.py` 再点击运行。完整设置与排错命令见 [`docs/MACOS_VSCODE_SETUP.md`](docs/MACOS_VSCODE_SETUP.md)。`.vscode/` 是本机配置，已被 Git 忽略。

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
MOUSE_MOVER_DURATION=0.4
STOP_HOTKEY=ctrl+option+s
RANDOM_AREA_WIDTH=800
RANDOM_AREA_HEIGHT=600
MANUAL_MOVE_THRESHOLD=60
MANUAL_IDLE_SECONDS=3
```

`common.env` 不覆盖进程中已经存在的环境变量。配置文件支持 `${NAME:-default}` 形式的变量展开。窗口内修改只影响本次运行，不会写回配置文件。

`MOUSE_MOVER_DURATION` 表示从起点移动到目标点的单程耗时，单位为秒，允许范围是 `0.05` 至 `5`。数值越大，移动越缓慢；默认值 `0.4` 会按约 60 FPS 使用缓入缓出轨迹移动。

固定移动模式会平滑移出并返回每轮起点。启用“随机范围移动”后，程序改用连续随机游走：以开始时的鼠标位置为矩形中心，每一段都从当前坐标计算下一个目标，并限制在 GUI 设置的宽度和高度内；停止时保留当前鼠标位置。运行期间会显示闪烁红框，直观标示当前随机范围。

随机范围移动和随机附加延迟默认启用。随机模式支持人工接管：鼠标相对程序预期位置偏移达到“人工移动阈值”时，自动移动立即暂停，日志显示检测结果，底部进度条变为满格黄色，范围红框继续显示。当鼠标连续静止达到“静止后恢复”时间后，程序把当前位置作为新锚点，重新构建同样大小的矩形、更新红框位置并恢复随机移动。默认矩形为 `800 × 600` 像素、随机距离为 `5–40` 像素、随机附加延迟为 `0–10` 秒、阈值为 `60` 像素、静止等待为 `3` 秒；对应环境变量分别为 `RANDOM_AREA_WIDTH`、`RANDOM_AREA_HEIGHT`、`MANUAL_MOVE_THRESHOLD` 和 `MANUAL_IDLE_SECONDS`。

`STOP_HOTKEY` 是全局停止快捷键，默认值为 `ctrl+option+s`。快捷键至少需要一个修饰键，并包含一个普通键；也可在 GUI 中修改后点击“应用快捷键”。监听器独立于窗口焦点，应用在后台时仍能停止鼠标移动。

进度条会反映任务模式和停止原因：未启用定时器时保持滚动动画；启用定时器后以绿色进度按实际运行时间增长；检测到人工操作时满格显示黄色；通过全局快捷键停止后满格显示红色，直到下一次任务启动。

macOS 全局快捷键需要键盘监听权限。如果界面显示快捷键“不可用”，请在“系统设置 > 隐私与安全性”中的“输入监控”或“辅助功能”里允许实际启动应用的 VS Code、Terminal、Python 或打包应用，然后重新启动程序。

GUI 实时日志与磁盘日志均使用 `[YYYY-MM-DD HH:MM:SS]` 本地时间戳。源码运行时日志保存在项目的 `logs/mouse_mover.log`；macOS `.app` 的日志保存在 `~/Library/Logs/MouseMover/mouse_mover.log`。单文件最大 10 MB，保留 5 份备份。界面的“清空界面日志”不会删除磁盘日志。

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

macOS 本机构建（生成到 `build/macos-dist/`，验证后放到根目录）：

```bash
./.venv/bin/pyinstaller --clean --noconfirm \
  --distpath build/macos-dist --workpath build/macos-work MouseMover.spec
codesign --verify --deep --strict build/macos-dist/MouseMover.app
```

`MouseMover.spec` 固定 Bundle ID、图标和项目版本，并嵌入配置与资源。验证完成后将新 App 放到项目根目录；替换前可将旧 App 移到 `build/` 留作备份。当前电脑没有可用的 Apple 开发者签名身份，因此本机构建使用临时签名。临时签名的身份会随构建变化，重建后通常需要重新授权辅助功能；若长期分发，应使用稳定的 Apple 开发者证书签名并公证。

当前 macOS 构建产物位于项目根目录 `MouseMover.app`，可在 Finder 中双击启动。若系统提示未获辅助功能权限，请在“系统设置 > 隐私与安全性 > 辅助功能”中核对授权条目对应的文件路径：移到 `build/` 的旧版 App 即使开关仍为开启，也不会授权根目录的新 App。应添加并开启根目录的 `MouseMover.app`，然后完全退出并重新打开。详情见 [`docs/MACOS_VSCODE_SETUP.md`](docs/MACOS_VSCODE_SETUP.md)。

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
