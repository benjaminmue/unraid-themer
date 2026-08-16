#!/usr/bin/env python3
"""
check_contrast.py — verify that every theme's button labels are readable, and
optionally fix the ones that are not.

Filled buttons take the theme's accent as background. A hard-coded white label
on a light accent (Nord's #88c0d0, Catppuccin's #cba6f7) lands near 2:1, which
WCAG AA misses by a mile — the text is effectively gone. The rule applied here
is the same one the theme builder uses: keep the theme's own background as the
label colour while it clears AA, so the button stays part of the palette;
otherwise fall back to whichever of black or white the accent tolerates better.

Run from anywhere:
  python3 scripts/check_contrast.py          # report only, non-zero on failure
  python3 scripts/check_contrast.py --fix    # rewrite the offending themes
"""
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES = os.path.join(REPO, "themes")
AA = 4.5

sys.path.insert(0, os.path.join(REPO, "scripts"))
from gen_swatches import read_root_vars, resolve, swatch_for  # noqa: E402  (same palette rules)

# The plugin ships its own copies (bebamu is built in, the rest are seeded to
# flash on first install). They are NOT byte-identical to the registry files, so
# they get checked in place rather than copied over.
BUNDLED = os.path.join(REPO, "plugin", "usr", "local", "emhttp", "plugins",
                       "unraid.themer")

BUTTON_BLOCK = re.compile(r'(input\[type="button"\][^{]*\{)([^}]*)(\})', re.S)
COLOR_DECL = re.compile(r'(color\s*:\s*)([^;!]+?)(\s*!important)?(?=\s*;)')
BTN_VAR = re.compile(r'(--button-text-color\s*:\s*)([^;]+)(;)')


def luminance(hex_color):
    channels = []
    for i in (1, 3, 5):
        v = int(hex_color[i:i + 2], 16) / 255
        channels.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b):
    l1, l2 = luminance(a), luminance(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def button_text(accent, background):
    """The readable label colour, same rule as themer_button_text() in PHP.

    The theme's own background is preferred so the button stays part of the
    palette, but only while it clears AA. Otherwise fall back to whichever of
    black or white the accent tolerates better."""
    if contrast(background, accent) >= AA:
        return background
    return "#000000" if contrast("#000000", accent) >= contrast("#ffffff", accent) else "#ffffff"


def current_label(css, variables):
    """The colour the filled-button rule actually paints its text with."""
    match = BUTTON_BLOCK.search(css)
    if not match:
        return None
    decl = COLOR_DECL.search(match.group(2))
    return resolve(decl.group(2).strip(), variables) if decl else None


def targets():
    """Every stylesheet whose buttons a user can end up looking at."""
    with open(os.path.join(THEMES, "index.json"), encoding="utf-8") as fh:
        index = json.load(fh)
    for theme in index["themes"]:
        yield theme["name"], os.path.join(THEMES, theme["file"])
    for folder in ("defaults", "presets"):
        pattern = os.path.join(BUNDLED, folder, "*.css")
        for path in sorted(glob.glob(pattern)):
            yield f"{folder}/{os.path.basename(path)[:-4]}", path


def main():
    fix = "--fix" in sys.argv
    failures, fixed = [], 0
    for name, path in targets():
        with open(path, encoding="utf-8") as fh:
            css = fh.read()
        variables = read_root_vars(css)
        # palette straight from the file, so bundled copies need no registry entry
        swatch, missing = swatch_for(path)
        if missing:
            failures.append(f"{os.path.basename(path)}: no colour for {', '.join(missing)}")
            continue
        background, accent = swatch[0], swatch[3]
        label = current_label(css, variables)
        if not label:
            print(f"{name:26} no filled-button rule, skipped")
            continue

        ratio = contrast(label, accent)
        if round(ratio, 1) >= AA:
            print(f"{name:26} {label} on {accent}  {ratio:5.1f}:1  ok")
            continue

        wanted = button_text(accent, background)
        new_ratio = contrast(wanted, accent)
        print(f"{name:26} {label} on {accent}  {ratio:5.1f}:1  FAIL"
              f"  -> {wanted} would give {new_ratio:.1f}:1")
        if not fix:
            failures.append(f"{name}: button label {ratio:.1f}:1 (needs {AA})")
            continue
        if round(new_ratio, 1) < AA:
            failures.append(f"{name}: even the best label only reaches {new_ratio:.1f}:1")
            continue

        # rewrite the declaration inside the filled-button rule, and the
        # --button-text-color variable that other components read
        block = BUTTON_BLOCK.search(css)
        body = COLOR_DECL.sub(
            lambda m: m.group(1) + wanted + (' !important' if m.group(3) else ''),
            block.group(2), count=1)
        css = css[:block.start()] + block.group(1) + body + block.group(3) + css[block.end():]
        css = BTN_VAR.sub(lambda m: m.group(1) + wanted + m.group(3), css, count=1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(css)
        fixed += 1

    if fixed:
        print(f"\n{fixed} theme(s) rewritten.")
    if failures:
        print("\nFAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print(f"\nAll stylesheets pass the {AA}:1 button check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
