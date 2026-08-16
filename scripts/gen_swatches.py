#!/usr/bin/env python3
"""
gen_swatches.py — extract a 5-colour swatch from every theme in themes/ and
write it into themes/index.json as a "swatch" array, so the store can preview
a theme's palette before it is downloaded.

Themes declare their palette in different ways: the generated ones use the
compact --t-* variables, the hand-written ones only set Dynamix core variables.
Both are covered by a fallback chain per swatch slot, and var() references are
resolved. Only :root declarations are read — theme-scoped blocks such as
html.Theme--black are ignored, so a dual-mode theme reports its light palette.

Run from anywhere:  python3 scripts/gen_swatches.py [--check]
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES = os.path.join(REPO, "themes")

# swatch slot -> variable names in order of preference
SLOTS = {
    "bg":      ["--t-bg", "--background-color", "--ui-bg", "--background"],
    "surface": ["--t-surface", "--mild-background-color", "--shade-bg-color",
                "--table-background-color", "--ui-bg-elevated", "--card"],
    "text":    ["--t-text", "--text-color", "--ui-text", "--foreground"],
    "accent":  ["--t-accent", "--link-text-color", "--button-background",
                "--orange-500", "--brand-orange", "--ui-primary", "--primary"],
    "accent2": ["--t-accent2", "--brand-red", "--orange-800", "--accent",
                "--orange-300"],
}
ORDER = ["bg", "surface", "text", "accent", "accent2"]

ROOT_BLOCK = re.compile(r":root\s*\{(.*?)\}", re.S)
DECL = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+);")
VAR_REF = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,([^)]*))?\)")
HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
RGB = re.compile(r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})")


def read_root_vars(css):
    """All custom properties declared in :root blocks, later wins."""
    variables = {}
    for block in ROOT_BLOCK.findall(css):
        for name, value in DECL.findall(block):
            variables[name] = value.strip()
    return variables


def resolve(value, variables, depth=0):
    """Resolve var() chains to a literal colour, or None."""
    if value is None or depth > 8:
        return None
    value = value.strip()
    match = VAR_REF.search(value)
    if match:
        target = variables.get(match.group(1))
        if target is None and match.group(2):
            target = match.group(2)
        return resolve(target, variables, depth + 1)
    return to_hex(value)


def to_hex(value):
    """Normalise #rgb / #rrggbb / rgb() / rgba() to #rrggbb, else None."""
    value = value.strip().split("!")[0].strip()
    match = HEX.match(value)
    if match:
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        return "#" + digits.lower()
    match = RGB.search(value)
    if match:
        r, g, b = (min(255, int(match.group(i))) for i in (1, 2, 3))
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def swatch_for(path):
    """Returns (swatch list, list of unresolved slot names)."""
    with open(path, encoding="utf-8") as fh:
        variables = read_root_vars(fh.read())
    colors, missing = [], []
    for slot in ORDER:
        value = None
        for candidate in SLOTS[slot]:
            if candidate in variables:
                value = resolve(variables[candidate], variables)
                if value:
                    break
        if not value:
            missing.append(slot)
            # keep the array length stable so the UI can index it blindly
            value = colors[0] if colors else "#808080"
        colors.append(value)
    return colors, missing


def main():
    check_only = "--check" in sys.argv
    index_path = os.path.join(THEMES, "index.json")
    with open(index_path, encoding="utf-8") as fh:
        index = json.load(fh)

    changed, problems = 0, []
    for theme in index["themes"]:
        css_path = os.path.join(THEMES, theme["file"])
        if not os.path.isfile(css_path):
            problems.append(f"{theme['file']}: file missing")
            continue
        colors, missing = swatch_for(css_path)
        if missing:
            problems.append(f"{theme['file']}: no colour found for {', '.join(missing)}")
        if theme.get("swatch") != colors:
            theme["swatch"] = colors
            changed += 1
        print(f"{theme['name']:24} {' '.join(colors)}")

    if problems:
        print("\nWARNUNG:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)

    if check_only:
        if changed:
            print(f"\n{changed} theme(s) would change — run without --check.", file=sys.stderr)
        return 1 if (changed or problems) else 0

    if changed:
        with open(index_path, "w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    print(f"\n{changed} of {len(index['themes'])} entries updated.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
