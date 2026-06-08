# print-file Codex Skill

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
