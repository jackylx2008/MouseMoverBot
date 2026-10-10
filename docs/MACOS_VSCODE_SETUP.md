# macOS 与 VS Code 启动说明

本文说明如何在 macOS 上使用项目虚拟环境启动 Mouse Mover，以及如何解决 VS Code Code Runner 使用错误 Python 解释器的问题。

## 1. 确认项目环境

在 VS Code 打开项目根目录，然后在集成终端执行：

```bash
pwd
./venv/bin/python --version
./venv/bin/python -m pip check
./venv/bin/python mouse_mover.py --check
```

当前仓库已有的环境目录名是 `venv/`。如果在另一台机器按 README 新建了 `.venv/`，请把本文命令中的 `venv` 替换为 `.venv`。

若环境尚未创建：

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Homebrew Python 如果缺少 Tkinter，可安装与 Python 次版本一致的组件。例如 Python 3.14：

```bash
brew install python-tk@3.14
```

安装后应重新创建虚拟环境，确保环境引用当前 Homebrew Python。

## 2. 推荐启动方式

不依赖 shell 激活状态，直接调用项目解释器：

```bash
./venv/bin/python mouse_mover.py
```

或者先激活环境：

```bash
source venv/bin/activate
python mouse_mover.py
```

首次运行时，macOS 可能要求辅助功能权限。请在“系统设置 > 隐私与安全性 > 辅助功能”中允许实际启动程序的终端、VS Code、Python 或打包后的应用。

## 3. VS Code Python 扩展

打开命令面板 `Command + Shift + P`，运行：

```text
Python: Select Interpreter
```

选择项目中的解释器：

```text
<项目目录>/venv/bin/python
```

随后使用编辑器右上角的 “Run Python File” 或 “Run Python File in Terminal”。这种方式由 VS Code Python 扩展管理，通常会使用刚才选择的解释器。

## 4. Code Runner 配置

Code Runner 不保证沿用 Python 扩展选择的解释器。要继续使用 “Run Code”，请在本机创建 `.vscode/settings.json`：

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "code-runner.executorMap": {
    "python": "\"$workspaceRoot/venv/bin/python\" -u \"$fullFileName\""
  },
  "code-runner.fileDirectoryAsCwd": true,
  "code-runner.ignoreSelection": true,
  "code-runner.runInTerminal": false,
  "code-runner.clearPreviousOutput": true
}
```

保存后运行 `Developer: Reload Window`，重新打开根目录的 `mouse_mover.py`，再执行 “Run Code”。

项目已在 `.gitignore` 中忽略 `.vscode/`。该文件属于当前电脑的 IDE 配置，不应依赖 Git 在 Windows 和 macOS 之间复用。

## 5. 判断是否使用了正确解释器

正确的 Code Runner 输出命令应同时包含项目环境和入口文件，例如：

```text
<项目目录>/venv/bin/python -u <项目目录>/mouse_mover.py
```

如果命令开头是下面任一种形式，说明仍在使用系统解释器：

```text
python
python3
/usr/bin/python3
/opt/homebrew/bin/python3
```

可分别检查系统解释器和项目解释器：

```bash
python3 -c "import sys; print(sys.executable)"
./venv/bin/python -c "import sys; print(sys.executable)"
```

第二条命令输出的路径必须位于当前项目的 `venv/bin/` 中。

## 6. 常见错误

### 提示安装 requirements.txt

程序检测不到 Quartz 时会提示：

```text
python -m pip install -r requirements.txt
```

如果依赖已经安装到 `venv/`，这通常不是需要重复安装，而是启动器选错了解释器。先执行：

```bash
./venv/bin/python -m pip show PyYAML pyobjc-framework-Quartz
./venv/bin/python mouse_mover.py --check
```

两条命令成功后，应修正 Code Runner 配置，而不是向系统 Python 重复安装依赖。

### 缺少 `_tkinter`

```text
ModuleNotFoundError: No module named '_tkinter'
```

安装匹配的 `python-tk` 后重新创建虚拟环境：

```bash
brew install python-tk@3.14
```

### Code Runner 只打开 Python 提示符

如果输出出现 `>>>`，说明命令没有带入口文件，或 Code Runner 复用了仍停留在 Python REPL 的终端。确认执行器中包含 `$fullFileName`，关闭旧的 Code 终端，然后执行 `Developer: Reload Window`。

### macOS 辅助功能未授权

若程序提示无法发布鼠标事件，请在 macOS 辅助功能列表中授权实际运行程序的应用。通过 VS Code 启动时通常需要授权 VS Code；通过 Terminal 启动时通常需要授权 Terminal 或所用终端应用。
