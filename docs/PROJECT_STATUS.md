# Mouse Mover 项目进度

更新时间：2026-10-14

当前版本：2.0.0

当前阶段：macOS 源码与 `.app` 实机验收通过，等待 Windows 11 实机验收

## 新 Mac mini 环境（2026-10-14）

- 使用 Apple Silicon、Python 3.13.16、Tk 9.0 和 `uv` 新建 `.venv/`，安装运行、开发与打包依赖。
- `main.py` 现调用正式入口 `mouse_mover.py`；本机 `.vscode/settings.json` 使 Code Runner 使用 `.venv/bin/python`。
- 25 项自动化测试通过，`uv pip check` 无冲突；恢复仓库中的 `.flake8` 配置后，静态检查也通过。
- 根目录 `MouseMover.app` 已用 PyInstaller 重新打包，版本为 2.0.0，arm64，签名完整性检查通过。
- 新版 App 与备份旧版 App 是不同的辅助功能授权对象。系统设置当前只显示已开启的旧版备份条目；根目录新版需要单独添加并开启后，再验收鼠标移动功能。
- 此电脑没有可用的 Apple 开发者签名身份，本地 App 使用临时签名。重新打包后可能需要重新授权辅助功能。

## 已完成

- 将旧版 PyQt5、`pywin32` 和 Windows 专用入口迁移为 Tkinter/ttk 跨平台界面。
- 建立 `src/mousemover/modules`、`src/mousemover/flows` 和根目录入口的分层结构。
- Windows 通过标准库 `ctypes` 调用 Win32 鼠标 API。
- macOS 通过 PyObjC Quartz 调用系统鼠标 API，并在启动时检查事件发布权限。
- 后台移动任务使用线程安全队列向 GUI 传递状态，后台线程不直接修改控件。
- 支持固定/随机距离、固定/随机延迟、定时停止和安全取消。
- 固定模式由瞬时跳转改为约 60 FPS 的缓入缓出往返移动，取消时平滑返回本轮起点。
- 修复随机模式反复返回启动锚点的问题；随机移动现在从当前坐标连续游走，停止时保留当前位置。
- 随机模式新增可配置矩形边界，并用闪烁红框标示当前活动范围。
- 修复活动范围红框四角重叠导致的十字和边框不闭合显示问题。
- 修复人工移动触发后红框被隐藏的问题；人工接管期间保持旧范围可见，结束后更新至新锚点。
- 将截图中的参数保存为默认值：随机范围和随机延迟默认启用，范围调整为 800 × 600 像素。
- 新增人工鼠标移动检测：达到阈值后暂停自动移动、记录界面日志并显示满格黄色状态；静止达到设定时间后，以人工停留点为新锚点恢复。
- 新增可配置的全局停止快捷键；macOS 窗口失去焦点后仍可停止鼠标移动。
- 进度条区分无限运行、定时运行、人工操作和快捷键停止：滚动、绿色计时、满格黄色暂停和满格红色停止状态。
- 配置迁移至根目录 `config.yaml`，支持 `common.env` 和 `${NAME:-default}` 覆盖。
- 接入控制台与滚动文件日志，运行文件写入 `logs/`。
- GUI 实时日志与磁盘日志统一使用秒级本地时间戳。
- 根目录生成 arm64 `MouseMover.app`，完成临时签名检查、嵌入资源检查和双击启动验证。
- 增加运行、开发和打包依赖声明及 PyInstaller 命令。
- 增加配置、移动算法、Windows 后端和隐藏 GUI 构建测试。
- 增加 macOS 下 VS Code Python 扩展与 Code Runner 的独立启动、解释器配置和排错说明。

## 已验证

### macOS 实机

- 2026-10-12 确认应用在 macOS 上运行正常，源码启动方式和人工接管事件链实机验收通过
- Python 3.14.8
- Tk 9.1
- PyYAML 6.0.3
- PyObjC Quartz 12.2.2
- Quartz 事件发布权限可用
- GUI 主窗口可启动并保持响应
- 鼠标可短距离移动并返回原位置；系统可能将 Quartz 浮点坐标取整到相邻像素
- `python mouse_mover.py --check` 通过
- 25 项自动化测试通过
- Flake8、`compileall`、`pip check` 和 `git diff --check` 通过
- wheel 构建通过

### macOS 验收结论

- 项目虚拟环境可正常加载运行依赖。
- `mouse_mover.py` 可正常启动桌面窗口。
- Quartz 鼠标移动后端工作正常。
- `Ctrl+Option+S` 全局键盘监听和停止回调在 macOS 实机验证通过。
- 人工大幅移动可触发自动暂停；静止后会以人工停留位置为新锚点恢复，macOS Quartz 实机事件链验证通过。
- 根目录 `MouseMover.app` 可通过 Finder 双击启动；首次启动会主动请求独立的辅助功能权限。
- 当前没有阻止 macOS 源码运行的已知问题。
- 面向其他 Mac 分发前仍需使用 Apple Developer 证书签名并完成公证。

### Windows 兼容层

- Win32 `GetCursorPos` / `SetCursorPos` 调用路径通过模拟测试。
- 平台专用依赖声明不会在 Windows 安装 macOS Quartz 包。
- Windows AppUserModelID 只在 Windows 分支调用。

## 待完成

- 在真实 Windows 11 设备上验证 GUI 启动、开始/停止、定时和随机模式。
- 在 Windows 多显示器及 125%/150% 缩放环境验证坐标行为。
- 在 Windows 11 上构建并启动 `.exe` 发布产物。
- 使用 Apple Developer 证书对 macOS `.app` 签名并完成公证。
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
