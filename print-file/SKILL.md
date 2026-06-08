---
name: print-file
description: Prepare and print local files from Codex on macOS/CUPS. Use when the user asks to print a file, print a PDF, single-sided print, double-sided print, manual duplex print, landscape/wide-content printing, inspect printer settings, fix PDF pages for printing, or troubleshoot jobs that submit but do not print.
---

# Print File

## Core Rules

- Treat printing as a physical side effect. Run a dry-run or inspection first unless the user explicitly says to print now.
- Before printing, identify the destination printer, page count, page sizes, and duplex support.
- Prefer `lp`/CUPS commands over GUI automation.
- Do not assume automatic duplex is available. Check `lpoptions -p <printer> -l` for `sides`, `Duplex`, or `Two-Sided` support.
- If a PDF has mixed page sizes or pages that fail to print, create an A4-normalized copy before printing.
- If printed output is garbled, do not send PDF directly. Convert the PDF to the printer-supported final format first, usually `image/urf` for IPP Everywhere printers.
- Treat `.urf` files as temporary spool artifacts. Use `print-urf --cleanup` after submitting jobs unless you explicitly need to keep the URF for debugging or reprinting.
- For wide or landscape content on fragile IPP/URF printers, do not assume a true landscape A4 PDF will print correctly. Prefer a portrait A4 PDF with the content rotated and scaled onto the page.
- For lab-specific printers, import a local config with `import-config`. Do not commit printer IPs, queue names, or site-specific feed notes to the public skill.

## Quick Workflow

1. Resolve the file path and confirm the file exists.
2. Run:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" inspect --file "<path>"
```

3. Inspect the active/default printer:

```bash
lpstat -d
lpstat -v
lpoptions -p "<printer>" -l
```

4. If the user requests normal single-sided printing, dry-run first:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print --file "<path>" --printer "<printer>" --paper A4 --fit --dry-run
```

5. For fragile IPP Everywhere printers, prefer URF printing. Use a configured printer alias when available:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" to-urf --file "<path>" --printer "<printer-or-alias>" --output "<path>.urf"
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print-urf --file "<path>.urf" --printer "<printer-or-alias>" --cleanup --dry-run
```

6. If the command is right and the user has clearly asked to print, run without `--dry-run` and with `--yes`.

## Automatic Duplex

Use only when the printer advertises duplex/sides support.

Long-edge binding is the normal choice for portrait A4 documents:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print --file "<path>" --printer "<printer>" --paper A4 --fit --duplex long --dry-run
```

Short-edge binding is for flip-up layouts.

If duplex is not supported, use the manual duplex workflow.

## Manual Duplex For PDFs

For printers without automatic duplex:

1. Prepare two PDFs:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" manual-duplex --file "<path>" --paper A4 --output-dir "<dir>"
```

This creates:

- `<name>_manual_duplex_front.pdf`: odd pages in normal order.
- `<name>_manual_duplex_back.pdf`: even pages in reverse order.

2. Print the front PDF.
3. Tell the user to put the printed stack back into the tray according to the known printer feed direction.
4. Print the back PDF.

For printers that garble PDF output, convert each generated PDF to URF before printing:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" to-urf --file "<front.pdf>" --printer "<printer>" --output "<front.urf>"
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print-urf --file "<front.urf>" --printer "<printer>" --cleanup --yes
```

For unknown feed direction, tell the user to test with a two-page sample before printing a full document.

## A4 Normalization

Use this when PDF printing fails for specific pages, pages have mixed sizes, or the printer waits for the wrong paper size:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" normalize-a4 --file "<path>" --pages "13-15" --output "<new.pdf>"
```

Then print the normalized output with `--paper A4 --fit`.

## Wide Or Landscape Content

Use this when the user asks for landscape printing, the PDF page is wider than tall, or prior output was cropped.

For some IPP/URF queues, avoid converting a true landscape A4 page directly to URF: `cupsfilter` can rasterize against portrait A4 and crop the right side. Instead, create a portrait A4 PDF where wide source pages are rotated 90 degrees and scaled inside the printable area:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" normalize-a4-rotated-wide --file "<path>" --output "<path>_A4_rotated_wide.pdf"
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" to-urf --file "<path>_A4_rotated_wide.pdf" --printer "<printer-or-alias>" --output "<path>_A4_rotated_wide.urf"
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print-urf --file "<path>_A4_rotated_wide.urf" --printer "<printer-or-alias>" --cleanup --yes
```

The paper exits as portrait A4; the user rotates the sheet to read it as landscape. This preserves all content and avoids the URF landscape-cropping failure.

## Temporary File Cleanup

After URF jobs are accepted by `lp`, delete the generated `.urf` file:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" print-urf --file "<path>.urf" --printer "<printer>" --cleanup --yes
```

Keep normalized PDFs in `_print_prepared/` only when useful for audit/reprint. Delete stale `.urf` files after successful jobs; they are large and reproducible from the prepared PDF.

## Local Configuration

Import lab or personal printer settings from a local JSON file:

```bash
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" import-config --file "<local-config.json>"
python3 "$HOME/.codex/skills/print-file/scripts/print_file.py" show-config
```

Config files may contain private queue names, printer URIs, or feed-direction notes. Keep real configs outside git, for example in `local/print-file.config.json`. Use `examples/print-file.config.example.json` as the public template.

## CUPS Diagnostics

Use these commands when a job submits but does not print:

```bash
lpstat -o
lpstat -t
cancel -a "<printer>"
```

Use `ipptool` for IPP printer capabilities when needed:

```bash
ipptool -tv ipp://<ip>/ipp/print get-printer-attributes.test
```

Look for:

- `printer-make-and-model`
- `document-format-supported`
- `sides-supported`
- `media-default`
- `media-ready`

## Safety Prompt

If the user says only "prepare", "how to print", or the request is ambiguous, do not submit a job. Provide the dry-run command and ask for confirmation.

If the user says "print this file" and the file/printer/page settings are clear, it is acceptable to submit the print job after a quick inspection.
