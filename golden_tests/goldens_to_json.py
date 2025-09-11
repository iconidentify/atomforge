#!/usr/bin/env python3
"""
goldens_to_json.py

Build a JSON array from .str/.txt golden pairs in a directory.

Each object looks like:
{
  "name": "<basename>",
  "hex": "<SPACE-SEPARATED UPPERCASE HEX BYTES>",
  "script": "<contents of .txt with any 'GID:' banner line removed>"
}
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Matches lines like:
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<< GID:   40-9736 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
GID_BANNER_RE = re.compile(r"^<{5,}.*\bGID:\s*\d+-\d+\b.*>{5,}\s*$")

def to_spaced_hex(data: bytes) -> str:
    # Same output shape as your one-liner: "40 01 01 00 ..."
    return " ".join(f"{b:02X}" for b in data)

def clean_script_text(text: str) -> str:
    # Normalize newlines and drop any GID banner lines.
    # Preserve all other lines exactly.
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    kept = [ln for ln in lines if not GID_BANNER_RE.match(ln)]
    # Avoid an extra trailing newline unless the source had one across the board
    # (kept as-is by joining with '\n')
    return "\n".join(kept).rstrip("\n")

def collect_pairs(src_dir: Path):
    # Pair by stem: foo.str + foo.txt
    by_stem = {}
    for p in src_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() in (".str", ".txt"):
            by_stem.setdefault(p.stem, {})[p.suffix.lower()] = p
    # Keep only stems that have both files
    pairs = []
    for stem, files in by_stem.items():
        if ".str" in files and ".txt" in files:
            pairs.append((stem, files[".str"], files[".txt"]))
        else:
            # You can warn on missing partner if you like:
            # print(f"Skipping '{stem}': missing {'txt' if '.txt' not in files else 'str'} file", file=sys.stderr)
            pass
    # Sort naturally by stem (lexicographic is fine for stems like 32-494)
    pairs.sort(key=lambda t: t[0])
    return pairs

def main():
    ap = argparse.ArgumentParser(description="Convert golden .str/.txt pairs into a JSON array.")
    ap.add_argument("directory", nargs="?", default=".", help="Directory containing golden pairs (default: current dir)")
    ap.add_argument("-o", "--out", default="golden.json", help="Output JSON path (default: golden.json)")
    ap.add_argument("--encoding", default="utf-8", help="Encoding to read .txt files (default: utf-8)")
    ap.add_argument("--strict-encoding", action="store_true",
                    help="Fail on text decode errors (default: replace undecodable chars)")
    args = ap.parse_args()

    src_dir = Path(args.directory).resolve()
    if not src_dir.exists() or not src_dir.is_dir():
        print(f"Error: '{src_dir}' is not a directory", file=sys.stderr)
        sys.exit(2)

    pairs = collect_pairs(src_dir)
    if not pairs:
        print("No .str/.txt pairs found.", file=sys.stderr)
        sys.exit(1)

    out_items = []
    for stem, str_path, txt_path in pairs:
        # Read the .str file as binary and make spaced uppercase hex
        data = str_path.read_bytes()
        hex_str = to_spaced_hex(data)

        # Read the .txt; strip GID banner if present
        errors = None if args.strict_encoding else "replace"
        text = txt_path.read_text(encoding=args.encoding, errors=errors)
        script = clean_script_text(text)

        out_items.append({
            "name": stem,
            "hex": hex_str,
            "script": script
        })

    out_path = Path(args.out)
    out_path.write_text(json.dumps(out_items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} with {len(out_items)} item(s).")

if __name__ == "__main__":
    main()
