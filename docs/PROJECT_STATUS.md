# Mouse Mover 项目进度

更新时间：2026-10-09

当前版本：2.0.0

当前阶段：macOS 实机验证完成，等待 Windows 11 实机验收

## 已完成

- 将旧版 PyQt5、`pywin32` 和 Windows 专用入口迁移为 Tkinter/ttk 跨平台界面。
- 建立 `src/mousemover/modules`、`src/mousemover/flows` 和根目录入口的分层结构。
- Windows 通过标准库 `ctypes` 调用 Win32 鼠标 API。
- macOS 通过 PyObjC Quartz 调用系统鼠标 API，并在启动时检查事件发布权限。
- 后台移动任务使用线程安全队列向 GUI 传递状态，后台线程不直接修改控件。
- 支持固定/随机距离、固定/随机延迟、定时停止和安全取消。
- 配置迁移至根目录 `config.yaml`，支持 `common.env` 和 `${NAME:-default}` 覆盖。
- 接入控制台与滚动文件日志，运行文件写入 `logs/`。
- 增加运行、开发和打包依赖声明及 PyInstaller 命令。
- 增加配置、移动算法、Windows 后端和隐藏 GUI 构建测试。

## 已验证

### macOS 实机

- Python 3.14.8
- Tk 9.1
- PyYAML 6.0.3
- PyObjC Quartz 12.2.2
- Quartz 事件发布权限可用
- GUI 主窗口可启动并保持响应
- 鼠标可短距离移动并返回原位置；系统可能将 Quartz 浮点坐标取整到相邻像素
- `python mouse_mover.py --check` 通过
- 9 项自动化测试通过
- Flake8、`compileall`、`pip check` 和 `git diff --check` 通过
- wheel 构建通过

### Windows 兼容层

- Win32 `GetCursorPos` / `SetCursorPos` 调用路径通过模拟测试。
- 平台专用依赖声明不会在 Windows 安装 macOS Quartz 包。
- Windows AppUserModelID 只在 Windows 分支调用。

## 待完成

- 在真实 Windows 11 设备上验证 GUI 启动、开始/停止、定时和随机模式。
- 在 Windows 多显示器及 125%/150% 缩放环境验证坐标行为。
- 分别构建并启动 Windows `.exe` 与 macOS `.app`。
- 根据实机结果补充平台截图或发布说明。

## 验收命令

```bash
python -m unittest discover -s tests -v
python -m flake8 mouse_mover.py logging_config.py src tests
python -m compileall -q mouse_mover.py logging_config.py src tests
python mouse_mover.py --check
python -m pip check
git diff --check
```
