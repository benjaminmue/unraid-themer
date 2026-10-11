#!/usr/bin/env python3
"""
sanitize_css.py — CI gate for the theme registry.

Validates every themes/*.css against the shared ruleset in css_rules.py
(mirrored by themer_css_violation in UnraidThemer.page) and checks themes/index.json for
consistency. Exits non-zero on any violation, so unsafe submissions fail the
GitHub Action and cannot be merged.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from css_rules import violations  # noqa: E402  (shared with the bots and, via the corpus test, the plugin)

VALID_BASE = {"any", "white", "black", "azure", "gray"}


def check_css(path):
    data = open(path, encoding="utf-8", errors="replace").read()
    errs = violations(data)
    if data.strip() == "":
        errs.append("empty")
    if data.count("{") != data.count("}"):
        errs.append("unbalanced braces")
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
