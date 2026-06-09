# print-file Codex Skill

用于 macOS/CUPS 的 Codex 打印 skill。它让 Codex 在打印前先检查文件和打印机能力，并用更稳的 CUPS/URF 流程处理容易乱码、裁切或需要手动双面的打印任务。

This is a Codex skill for safe local printing on macOS/CUPS. It teaches Codex to inspect files first, use CUPS commands, normalize PDFs, convert fragile jobs to `image/urf`, and clean temporary spool files.

## Quick Start

```bash
git clone git@github.com:water-lrx/print-file-skill.git
cd print-file-skill
./install.sh
```

The installer copies the skill to:

```bash
$HOME/.codex/skills/print-file
```

When updating an existing installation, `install.sh` preserves the installed `config/` directory.

Restart Codex after installing or updating the skill so it can reload the skill list.

## Import Printer Config

The public repository intentionally does not contain real lab printer IPs, CUPS queue names, or feed-direction notes. Those details belong in a local JSON config.

Create a local config from the template:

```bash
mkdir -p local
cp examples/print-file.config.example.json local/print-file.config.json
```

Edit `local/print-file.config.json`, then import it into the installed skill:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" import-config --file local/print-file.config.json
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" show-config
```

`local/` and `print-file/config/` are ignored by git. Share real lab configs privately, for example through a lab group file or direct message, not through the public repository.

## 给同学的安装步骤

1. 克隆仓库并安装：

```bash
git clone git@github.com:water-lrx/print-file-skill.git
cd print-file-skill
./install.sh
```

2. 获取实验室配置文件，例如 `print-file.config.json`。

3. 导入配置：

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" import-config --file /path/to/print-file.config.json
```

4. 重启 Codex。

5. 之后可以直接对 Codex 说：

```text
帮我单面打印这个 PDF
帮我双面打印这个文件
这个内容比较宽，横向打印
```

Codex 会根据 skill 检查文件、选择打印机、必要时转换 URF，并在提交后清理 `.urf` 临时文件。

如果要打印多份，直接说“打印两份/三份”。对于 URF 打印，skill 会自动拆成多个单份作业提交，避免部分 IPP 打印机忽略 `lp -n` 导致实际只出一份。

## For Other Agents

If you are an AI agent using this repository:

- Install the skill by running `./install.sh` from the repository root.
- If a local printer config is provided, import it with `print_file.py import-config --file <config.json>`.
- Never commit real printer configs, IP addresses, CUPS queue names, receipt screenshots, PDFs, `.urf` files, or `_print_prepared/` output.
- Before printing, inspect the file and printer state.
- Treat printing as a physical side effect. Use dry runs unless the user clearly asked to print.
- For fragile IPP Everywhere printers, prefer `to-urf` followed by `print-urf --cleanup`.
- For wide/landscape receipts that crop, use `normalize-a4-rotated-wide` before converting to URF.
- For multiple URF copies, use `print-urf --copies N`; it submits N separate one-copy jobs because some printers ignore CUPS copy counts for `image/urf`.
- For printers without automatic duplex, use the manual duplex workflow.

## Config Format

Public template:

[examples/print-file.config.example.json](examples/print-file.config.example.json)

Example shape:

```json
{
  "default_printer": "lab-hp",
  "printers": {
    "lab-hp": {
      "queue": "REPLACE_WITH_CUPS_QUEUE_NAME",
      "uri": "ipp://REPLACE_WITH_PRINTER_HOST_OR_IP/ipp/print",
      "model": "HP Laser MFP 136nw",
      "driver": "IPP Everywhere",
      "paper": "A4",
      "auto_duplex": false,
      "preferred_format": "image/urf"
    }
  }
}
```

After import, `--printer lab-hp` resolves to the configured CUPS queue.

## Common Commands

Inspect a PDF:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" inspect --file input.pdf
```

Normalize to A4:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" normalize-a4 --file input.pdf --output input_A4.pdf
```

By default, normalization centers smaller-than-A4 pages without enlarging them. This avoids making text and table lines look too dark after URF rasterization. Add `--allow-upscale` only when you intentionally want a small page enlarged to fill A4.

Fix wide or landscape content before URF conversion:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" normalize-a4-rotated-wide --file input.pdf --output input_A4_rotated_wide.pdf
```

Convert to URF and print, deleting the temporary URF afterward:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" to-urf --file input_A4.pdf --printer lab-hp --output input_A4.urf
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print-urf --file input_A4.urf --printer lab-hp --cleanup --yes
```

Print multiple URF copies as separate physical jobs:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print-urf --file input_A4.urf --printer lab-hp --copies 2 --cleanup --yes
```

Create manual duplex PDFs:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" manual-duplex --file input.pdf --paper A4 --output-dir .
```

## What This Skill Handles

- PDF inspection before printing.
- A4 normalization for mixed or awkward page sizes.
- Scale-preserving A4 normalization to avoid bold-looking output from unnecessary upscaling.
- URF conversion for IPP printers that garble direct PDFs.
- Wide/landscape receipt handling to avoid right-side cropping.
- Reliable multiple-copy URF printing by submitting separate one-copy jobs.
- Manual duplex preparation for printers without automatic duplex.
- Temporary `.urf` cleanup after job submission.

## Requirements

- macOS with CUPS commands such as `lp`, `lpstat`, `lpoptions`, and `cupsfilter`.
- Python 3.
- Python package `pypdf`.

## Privacy And Repository Hygiene

Do not commit:

- Real printer IP addresses or internal hostnames.
- CUPS queue names that identify a private lab printer.
- Local config files under `local/` or `print-file/config/`.
- PDFs, screenshots, receipts, reimbursement files, or generated print artifacts.
- `.urf` files or `_print_prepared/` directories.

The repository `.gitignore` is set up for this workflow, but agents should still run a quick scan before pushing.
