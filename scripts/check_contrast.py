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

The second check covers Community Applications. CA paints the app-detail popup
from --support-popup-background / --sidebar-background and their matching text
variables, all of which it takes from the BASE Dynamix theme rather than from
the preset. The compat block in every theme remaps that pair onto
--mild-background-color / --text-color, so those two have to clear AA against
each other or the popup text goes unreadable again.

Run from anywhere:
  python3 scripts/check_contrast.py          # report only, non-zero on failure
  python3 scripts/check_contrast.py --fix    # rewrite the offending themes
                                             # (buttons only; the CA pair is a
                                             #  palette choice, not a rewrite)
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
from gen_swatches import DECL, read_root_vars, resolve, swatch_for  # noqa: E402  (same palette rules)

# The plugin ships its own copies (bebamu is built in, the rest are seeded to
# flash on first install). They are NOT byte-identical to the registry files, so
# they get checked in place rather than copied over.
BUNDLED = os.path.join(REPO, "plugin", "usr", "local", "emhttp", "plugins",
                       "unraid.themer")

BUTTON_BLOCK = re.compile(r'(input\[type="button"\][^{]*\{)([^}]*)(\})', re.S)
COLOR_DECL = re.compile(r'(color\s*:\s*)([^;!]+?)(\s*!important)?(?=\s*;)')
BTN_VAR = re.compile(r'(--button-text-color\s*:\s*)([^;]+)(;)')
# bebamu keeps its dark values in html.Theme--black instead of a second :root,
# so that variant needs checking on its own or half the theme goes unmeasured.
DARK_BLOCK = re.compile(r"html\.Theme--black\s*\{(.*?)\}", re.S)


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


def variants(css):
    """(label, variables) for every light/dark set a stylesheet declares."""
    base = read_root_vars(css)
    yield "", base
    dark = {}
    for block in DARK_BLOCK.findall(css):
        for name, value in DECL.findall(block):
            dark[name] = value.strip()
    if dark:
        merged = dict(base)
        merged.update(dark)
        yield " dark", merged


def ca_popup(name, css):
    """Text against the surface CA's app-detail popup gets from the compat block.

    Returns the failure lines, empty when every variant clears AA."""
    failures = []
    for suffix, variables in variants(css):
        surface = resolve(variables.get("--mild-background-color"), variables)
        text = resolve(variables.get("--text-color"), variables)
        label = f"{name}{suffix}"
        if not surface or not text:
            missing = "--mild-background-color" if not surface else "--text-color"
            print(f"{label:26} {missing} unresolved, skipped")
            continue
        ratio = contrast(text, surface)
        verdict = "ok" if round(ratio, 1) >= AA else "FAIL"
        print(f"{label:26} {text} on {surface}  {ratio:5.1f}:1  {verdict}")
        if verdict == "FAIL":
            failures.append(f"{label}: CA popup text {ratio:.1f}:1 (needs {AA})")
    return failures


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
    print("Filled button labels on the accent")
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

    print("\nCommunity Applications popup text on the mild background")
    for name, path in targets():
        with open(path, encoding="utf-8") as fh:
            failures += ca_popup(name, fh.read())

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print(f"\nAll stylesheets pass both {AA}:1 checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
