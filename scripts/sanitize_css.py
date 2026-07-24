#!/usr/bin/env python3
"""
sanitize_css.py — CI gate for the theme registry.

Validates every themes/*.css against the same ruleset the plugin uses
(themer_sanitize_css in UnraidThemer.page) and checks themes/index.json for
consistency. Exits non-zero on any violation, so unsafe submissions fail the
GitHub Action and cannot be merged.
"""
import json
import os
import re
import sys

MAX_BYTES = 512 * 1024
BLOCKED = [
    (re.compile(r"<\s*script", re.I),                          "contains a <script> tag"),
    (re.compile(r"<\s*/?\s*(iframe|object|embed|base)", re.I),  "contains embedded HTML"),
    (re.compile(r"javascript\s*:", re.I),                      "contains a javascript: URI"),
    (re.compile(r"expression\s*\(", re.I),                     "contains a CSS expression()"),
    (re.compile(r"behaviou?r\s*:", re.I),                      "contains a CSS behavior:"),
    (re.compile(r"-moz-binding", re.I),                        "contains -moz-binding"),
    (re.compile(r"@import", re.I),                             "contains @import"),
    (re.compile(r"url\s*\(\s*['\"]?\s*(https?:|//)", re.I),     "loads an external url()"),
]
VALID_BASE = {"any", "white", "black", "azure", "gray"}


def check_css(path):
    errs = []
    data = open(path, encoding="utf-8", errors="replace").read()
    if len(data.encode("utf-8")) > MAX_BYTES:
        errs.append("file too large (>512 KB)")
    if data.strip() == "":
        errs.append("empty")
    if data.count("{") != data.count("}"):
        errs.append("unbalanced braces")
    for rx, why in BLOCKED:
        if rx.search(data):
            errs.append(why)
    return errs


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tdir = os.path.join(root, "themes")
    fail = False

    # index.json
    idx = os.path.join(tdir, "index.json")
    try:
        index = json.load(open(idx, encoding="utf-8"))
    except Exception as e:
        print(f"::error::themes/index.json is not valid JSON: {e}")
        sys.exit(1)

    listed = set()
    for t in index.get("themes", []):
        for k in ("name", "file", "author", "base", "description"):
            if k not in t:
                print(f"::error::index entry missing '{k}': {t}")
                fail = True
        listed.add(t.get("file"))
        if t.get("base") not in VALID_BASE:
            print(f"::error::index entry '{t.get('file')}' has invalid base '{t.get('base')}'")
            fail = True
        fp = os.path.join(tdir, t.get("file", ""))
        if not os.path.isfile(fp):
            print(f"::error::index references missing file '{t.get('file')}'")
            fail = True

    # every css file
    for fn in sorted(os.listdir(tdir)):
        if not fn.endswith(".css"):
            continue
        errs = check_css(os.path.join(tdir, fn))
        for e in errs:
            print(f"::error file=themes/{fn}::{fn}: {e}")
            fail = True
        if fn not in listed:
            print(f"::warning file=themes/{fn}::{fn} is not listed in index.json")
        if not errs:
            print(f"ok: {fn}")

    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
