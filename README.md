# print-file Codex Skill

## 中文说明

这是一个用于 macOS/CUPS 打印的 Codex skill，可以帮助 Codex 更稳地处理本地文件打印任务。

### 功能

- 打印前检查 PDF 页数和页面尺寸。
- 通过 CUPS 的 `lp` 命令提交打印任务。
- 对容易直接打印乱码的 IPP Everywhere 打印机，先转换为 `image/urf` 再打印。
- 将 PDF 归一化到 A4 页面。
- 处理横向或较宽票据，避免右侧内容被裁切。
- 支持无自动双面打印机的手动双面流程。
- 打印提交后自动清理临时 `.urf` 文件。

### 安装

克隆仓库后运行：

```bash
./install.sh
```

安装位置：

```bash
$HOME/.codex/skills/print-file
```

安装或更新后，请重启 Codex，让 skill 列表重新加载。

### 导入本地打印机配置

公开仓库不应包含实验室打印机 IP、队列名、进纸方向等内部信息。请把这些信息放在本地 JSON 配置里，安装后导入：

```bash
mkdir -p local
cp examples/print-file.config.example.json local/print-file.config.json
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" import-config --file local/print-file.config.json
```

`local/` 已被 git 忽略。真实实验室配置请通过私有渠道共享，不要提交到公开仓库。

导入后可以查看配置，并使用配置里的打印机别名：

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" show-config
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print-urf --file input.urf --printer lab-hp --cleanup --yes
```

### 注意事项

- 该 skill 面向 macOS，并依赖系统 CUPS 命令。
- `scripts/print_file.py` 需要 Python 包 `pypdf`。
- `.urf` 是临时打印中间文件，提交打印时建议使用 `--cleanup` 自动删除。

## English

A Codex skill for preparing and printing local files on macOS/CUPS.

## Features

- Inspect PDF page count and page sizes before printing.
- Print through CUPS with `lp`.
- Convert PDFs to `image/urf` for IPP Everywhere printers that garble direct PDF output.
- Normalize PDFs to A4.
- Handle wide/landscape receipts without right-side cropping.
- Support manual duplex for printers without automatic duplex.
- Clean temporary `.urf` spool files after print submission.

## Install

Clone this repository, then run:

```bash
./install.sh
```

This installs the skill to:

```bash
$HOME/.codex/skills/print-file
```

Restart Codex after installing or updating the skill.

## Local Printer Configuration

Printer queues, IP addresses, and lab-specific feed notes should not be committed to the public skill. Keep them in a local JSON config and import it after installation:

```bash
cp examples/print-file.config.example.json local/print-file.config.json
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" import-config --file local/print-file.config.json
```

`local/` is ignored by git. Share real lab config through a private channel, not in the public repository.

After importing, you can use the configured alias:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" show-config
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print-urf --file input.urf --printer lab-hp --cleanup --yes
```

## Notes

- This skill assumes macOS with CUPS commands available.
- Python package `pypdf` is required by `scripts/print_file.py`.
- URF files are temporary and should be printed with `--cleanup`.
