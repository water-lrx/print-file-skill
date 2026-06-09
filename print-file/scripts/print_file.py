#!/usr/bin/env python3
"""Small CUPS/PDF helper for the print-file skill."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
import shutil
from pathlib import Path

A4_W = 595.2756
A4_H = 841.8898
SKILL_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_DIR / "config" / "print-file.config.json"


def require_pypdf():
    try:
        from pypdf import PdfReader, PdfWriter, Transformation
    except Exception as exc:  # pragma: no cover - depends on local Python env
        raise SystemExit(
            "pypdf is required. Use the bundled Codex Python if system python lacks it."
        ) from exc
    return PdfReader, PdfWriter, Transformation


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def parse_pages(spec: str | None, total: int | None = None) -> list[int] | None:
    if not spec:
        return None
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start, end = int(left), int(right)
            step = 1 if end >= start else -1
            pages.extend(range(start, end + step, step))
        else:
            pages.append(int(part))
    if total is not None:
        bad = [p for p in pages if p < 1 or p > total]
        if bad:
            raise SystemExit(f"Page(s) out of range for {total}-page document: {bad}")
    return pages


def default_printer() -> str | None:
    try:
        out = subprocess.check_output(["lpstat", "-d"], text=True).strip()
    except Exception:
        return None
    marker = "："
    if marker in out:
        return out.split(marker, 1)[1].strip()
    if ":" in out:
        return out.split(":", 1)[1].strip()
    return None


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid config JSON: {CONFIG_PATH}: {exc}") from exc


def resolve_printer(name: str | None) -> str | None:
    if name:
        config = load_config()
        printers = config.get("printers", {})
        if isinstance(printers, dict) and name in printers:
            printer = printers[name]
            if isinstance(printer, dict):
                return printer.get("queue") or name
        return name
    config = load_config()
    default_alias = config.get("default_printer")
    printers = config.get("printers", {})
    if isinstance(default_alias, str) and isinstance(printers, dict) and default_alias in printers:
        printer = printers[default_alias]
        if isinstance(printer, dict) and printer.get("queue"):
            return printer["queue"]
    return default_printer()


def cmd_import_config(args: argparse.Namespace) -> int:
    src = Path(args.file).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"Config file not found: {src}")
    with src.open("r", encoding="utf-8") as fh:
        json.load(fh)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, CONFIG_PATH)
    print(str(CONFIG_PATH))
    return 0


def cmd_show_config(args: argparse.Namespace) -> int:
    config = load_config()
    print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


def inspect_pdf(path: Path) -> dict:
    PdfReader, _, _ = require_pypdf()
    reader = PdfReader(str(path))
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        pages.append(
            {
                "page": idx,
                "width_pt": round(float(page.mediabox.width), 4),
                "height_pt": round(float(page.mediabox.height), 4),
                "rotate": page.get("/Rotate"),
                "has_annotations": bool(page.get("/Annots")),
            }
        )
    return {
        "file": str(path),
        "type": "pdf",
        "page_count": len(reader.pages),
        "pages": pages,
    }


def cmd_inspect(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    result = {"file": str(path), "exists": True, "suffix": path.suffix.lower()}
    if is_pdf(path):
        result.update(inspect_pdf(path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def normalize_pdf_to_a4_pages(
    src: Path,
    out: Path,
    pages: list[int],
    keep_annots: bool,
    rotate_wide: bool = False,
) -> None:
    PdfReader, PdfWriter, Transformation = require_pypdf()
    reader = PdfReader(str(src))
    writer = PdfWriter()
    for page_num in pages:
        src_page = reader.pages[page_num - 1]
        if not keep_annots and "/Annots" in src_page:
            del src_page["/Annots"]
        new_page = writer.add_blank_page(width=A4_W, height=A4_H)
        width = float(src_page.mediabox.width)
        height = float(src_page.mediabox.height)
        if rotate_wide and width > height:
            # Keep the output sheet portrait A4. Some IPP/URF paths crop true landscape pages.
            margin = 24
            scale = min((A4_W - 2 * margin) / height, (A4_H - 2 * margin) / width)
            x = (A4_W - height * scale) / 2 + height * scale
            y = (A4_H - width * scale) / 2
            transform = Transformation().rotate(90).scale(scale).translate(x, y)
        else:
            scale = min(A4_W / width, A4_H / height)
            x = (A4_W - width * scale) / 2
            y = (A4_H - height * scale) / 2
            transform = Transformation().scale(scale).translate(x, y)
        new_page.merge_transformed_page(src_page, transform)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        writer.write(fh)


def normalize_pdf_to_a4(src: Path, out: Path, pages_spec: str | None, keep_annots: bool) -> None:
    PdfReader, _, _ = require_pypdf()
    reader = PdfReader(str(src))
    pages = parse_pages(pages_spec, len(reader.pages)) or list(range(1, len(reader.pages) + 1))
    normalize_pdf_to_a4_pages(src, out, pages, keep_annots)


def cmd_normalize_a4(args: argparse.Namespace) -> int:
    src = Path(args.file).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"File not found: {src}")
    if not is_pdf(src):
        raise SystemExit("normalize-a4 currently supports PDF input only.")
    out = Path(args.output).expanduser().resolve() if args.output else src.with_name(f"{src.stem}_A4.pdf")
    normalize_pdf_to_a4(src, out, args.pages, args.keep_annots)
    print(str(out))
    return 0


def cmd_normalize_a4_rotated_wide(args: argparse.Namespace) -> int:
    src = Path(args.file).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"File not found: {src}")
    if not is_pdf(src):
        raise SystemExit("normalize-a4-rotated-wide currently supports PDF input only.")
    PdfReader, _, _ = require_pypdf()
    reader = PdfReader(str(src))
    pages = parse_pages(args.pages, len(reader.pages)) or list(range(1, len(reader.pages) + 1))
    out = (
        Path(args.output).expanduser().resolve()
        if args.output
        else src.with_name(f"{src.stem}_A4_rotated_wide.pdf")
    )
    normalize_pdf_to_a4_pages(src, out, pages, args.keep_annots, rotate_wide=True)
    print(str(out))
    return 0


def cmd_manual_duplex(args: argparse.Namespace) -> int:
    src = Path(args.file).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"File not found: {src}")
    if not is_pdf(src):
        raise SystemExit("manual-duplex currently supports PDF input only.")
    PdfReader, _, _ = require_pypdf()
    total = len(PdfReader(str(src)).pages)
    pages = parse_pages(args.pages, total) or list(range(1, total + 1))
    front = [p for p in pages if p % 2 == 1]
    back = list(reversed([p for p in pages if p % 2 == 0]))
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else src.parent
    front_out = out_dir / f"{src.stem}_manual_duplex_front.pdf"
    back_out = out_dir / f"{src.stem}_manual_duplex_back.pdf"
    if front:
        normalize_pdf_to_a4_pages(src, front_out, front, keep_annots=False)
    if back:
        normalize_pdf_to_a4_pages(src, back_out, back, keep_annots=False)
    print(
        json.dumps(
            {
                "front": str(front_out) if front else None,
                "back": str(back_out) if back else None,
                "front_pages": front,
                "back_pages": back,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def build_lp_command(args: argparse.Namespace) -> list[str]:
    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    printer = resolve_printer(args.printer)
    if not printer:
        raise SystemExit("No printer provided and no default printer found.")
    cmd = ["lp", "-d", printer]
    if args.copies:
        cmd.extend(["-n", str(args.copies)])
    if args.pages:
        cmd.extend(["-P", args.pages])
    if args.paper:
        cmd.extend(["-o", f"media={args.paper}"])
    if args.fit:
        cmd.extend(["-o", "fit-to-page"])
    if args.duplex == "long":
        cmd.extend(["-o", "sides=two-sided-long-edge"])
    elif args.duplex == "short":
        cmd.extend(["-o", "sides=two-sided-short-edge"])
    elif args.duplex == "off":
        cmd.extend(["-o", "sides=one-sided"])
    cmd.append(str(path))
    return cmd


def ppd_path_for_printer(printer: str) -> Path:
    ppd = Path("/private/etc/cups/ppd") / f"{printer}.ppd"
    if not ppd.exists():
        raise SystemExit(f"PPD not found for printer {printer}: {ppd}")
    return ppd


def cmd_to_urf(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    printer = resolve_printer(args.printer)
    if not printer:
        raise SystemExit("No printer provided and no default printer found.")
    out = Path(args.output).expanduser().resolve() if args.output else path.with_suffix(".urf")
    ppd = ppd_path_for_printer(printer)
    cmd = ["cupsfilter", "-p", str(ppd), "-m", "image/urf", str(path)]
    if args.dry_run:
        print(" ".join(shlex.quote(part) for part in cmd) + f" > {shlex.quote(str(out))}")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        subprocess.run(cmd, check=True, stdout=fh)
    print(str(out))
    return 0


def cmd_print_urf(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    printer = resolve_printer(args.printer)
    if not printer:
        raise SystemExit("No printer provided and no default printer found.")
    copies = max(args.copies or 1, 1)
    cmd = ["lp", "-d", printer, "-o", "document-format=image/urf", "-n", "1"]
    if args.paper:
        cmd.extend(["-o", f"media={args.paper}"])
    if args.duplex == "long":
        cmd.extend(["-o", "sides=two-sided-long-edge"])
    elif args.duplex == "short":
        cmd.extend(["-o", "sides=two-sided-short-edge"])
    elif args.duplex == "off":
        cmd.extend(["-o", "sides=one-sided"])
    cmd.append(str(path))
    for copy_num in range(1, copies + 1):
        prefix = f"[copy {copy_num}/{copies}] " if copies > 1 else ""
        print(prefix + " ".join(shlex.quote(part) for part in cmd))
    if args.dry_run:
        return 0
    if not args.yes:
        raise SystemExit("Refusing to submit print job without --yes. Re-run with --yes after checking the command.")
    for _ in range(copies):
        subprocess.run(cmd, check=True)
    if args.cleanup:
        wait_seconds = max(args.cleanup_delay, 0)
        if wait_seconds:
            time.sleep(wait_seconds)
        try:
            path.unlink()
            print(f"deleted {path}")
        except FileNotFoundError:
            pass
    return 0


def cmd_print(args: argparse.Namespace) -> int:
    cmd = build_lp_command(args)
    print(" ".join(shlex.quote(part) for part in cmd))
    if args.dry_run:
        return 0
    if not args.yes:
        raise SystemExit("Refusing to submit print job without --yes. Re-run with --yes after checking the command.")
    subprocess.run(cmd, check=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect, repair, and print files through CUPS.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inspect", help="Inspect file metadata and PDF pages.")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("import-config", help="Import a local printer configuration JSON into the installed skill.")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_import_config)

    p = sub.add_parser("show-config", help="Show the imported local printer configuration.")
    p.set_defaults(func=cmd_show_config)

    p = sub.add_parser("normalize-a4", help="Create an A4-normalized PDF.")
    p.add_argument("--file", required=True)
    p.add_argument("--pages", help='Page list such as "1,3,5-8" or "14,12,10".')
    p.add_argument("--output")
    p.add_argument("--keep-annots", action="store_true")
    p.set_defaults(func=cmd_normalize_a4)

    p = sub.add_parser(
        "normalize-a4-rotated-wide",
        help="Create portrait A4 PDF pages, rotating wide source pages to fit without URF landscape cropping.",
    )
    p.add_argument("--file", required=True)
    p.add_argument("--pages", help='Page list such as "1,3,5-8" or "14,12,10".')
    p.add_argument("--output")
    p.add_argument("--keep-annots", action="store_true")
    p.set_defaults(func=cmd_normalize_a4_rotated_wide)

    p = sub.add_parser("manual-duplex", help="Create front/back PDFs for manual duplex printing.")
    p.add_argument("--file", required=True)
    p.add_argument("--pages", help="Optional subset of pages to duplex.")
    p.add_argument("--paper", default="A4")
    p.add_argument("--output-dir")
    p.set_defaults(func=cmd_manual_duplex)

    p = sub.add_parser("print", help="Build or submit an lp print command.")
    p.add_argument("--file", required=True)
    p.add_argument("--printer")
    p.add_argument("--pages")
    p.add_argument("--copies", type=int, default=1)
    p.add_argument("--paper", default="A4")
    p.add_argument("--fit", action="store_true")
    p.add_argument("--duplex", choices=["off", "long", "short"], default="off")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true", help="Submit the print job.")
    p.set_defaults(func=cmd_print)

    p = sub.add_parser("to-urf", help="Convert an input document to printer-ready image/urf.")
    p.add_argument("--file", required=True)
    p.add_argument("--printer")
    p.add_argument("--output")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_to_urf)

    p = sub.add_parser("print-urf", help="Print an image/urf file with explicit document-format.")
    p.add_argument("--file", required=True)
    p.add_argument("--printer")
    p.add_argument("--copies", type=int, default=1)
    p.add_argument("--paper", default="A4")
    p.add_argument("--duplex", choices=["off", "long", "short"], default="off")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true", help="Submit the print job.")
    p.add_argument("--cleanup", action="store_true", help="Delete the URF file after lp accepts the job.")
    p.add_argument(
        "--cleanup-delay",
        type=float,
        default=1.0,
        help="Seconds to wait before deleting the URF file when --cleanup is used.",
    )
    p.set_defaults(func=cmd_print_urf)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
