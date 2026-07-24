#!/usr/bin/env python3
"""
build.py — assemble the inline unraid-themer.plg from the source tree.

The plugin is fully self-contained (no .txz, no external assets): every file
under plugin/usr/local/emhttp/plugins/unraid.themer/ is embedded into the .plg
as a CDATA <FILE> block. Unraid re-runs the .plg on every boot, which recreates
these files in the RAM webroot. User data (config + custom.css) lives on the
flash and is restored to the webroot by the boot script.

Usage:  python3 build.py
Output: ./unraid-themer.plg
"""
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
NAME = "unraid.themer"
SRC = os.path.join(REPO, "plugin", "usr", "local", "emhttp", "plugins", NAME)
WEBROOT = f"/usr/local/emhttp/plugins/{NAME}"
FLASH = f"/boot/config/plugins/{NAME}"

META = {
    "name": NAME,
    "author": "benjaminmue",
    "version": "2026.07.24j",
    "launch": "Settings/UnraidThemer",
    "pluginURL": "https://github.com/benjaminmue/unraid-themer/raw/refs/heads/main/unraid-themer.plg",
    "support": "https://github.com/benjaminmue/unraid-themer",
    "min": "7.0.0",
    "icon": "paint-brush",
}

CHANGES = """## Unraid Themer
## 2026.07.24j
- Fix layout: "Added themes" remove buttons no longer span full width; the
  theme store list now stays in the form column instead of breaking left.

## 2026.07.24i
- Remove themes you added: imported / store themes show under "Added themes"
  with a remove button (built-in presets stay).

## 2026.07.24h
- Added 4 light themes (Catppuccin Latte, Solarized Light, Rose Pine Dawn,
  GitHub Light) — bundled and in the store.
- Store browser: search box + Light/Dark filter + scrollable list (scales to
  many themes).
- Preset help now notes the base is auto-paired on Apply.

## 2026.07.24g
- Store browser now uses a non-CDN-cached URL so newly published themes appear
  immediately (added Catppuccin Mocha to the registry).

## 2026.07.24f
- Theme store (mode B): browse the community registry in the settings page and
  download themes on demand (validated before saving). Already-installed themes
  are marked. Backed by a GitHub Action that sanitises every submitted theme.

## 2026.07.24e
- Theme store (mode A): import a community theme from a raw .css URL. The CSS
  is validated (scripts, javascript:, @import and external url() rejected)
  before it is saved and added to the preset dropdown.

## 2026.07.24d
- Auto-pair the base theme: selecting a dark preset now switches the Dynamix
  base to Black on Apply (via Unraid's own config writer) so the Vue
  web-components (notifications panel) and Community Apps render dark too.

## 2026.07.24c
- Plugins list: restore the plugin title (use a bold first line, not an H1).

## 2026.07.24b
- CRITICAL: loader no longer leaks PHP globals ($name etc.) — this broke
  navigation to Share / Disk / Device settings pages (they use a global $name).
  The loader now runs inside an isolated closure.
- Plugins page: removed the README heading that rendered the name oversized.

## 2026.07.24a
- Dark presets: fix light table rows, Community Apps cards and "white bars"
  (remap Dynamix tablesorter + CA variables to the preset's own colors).
- Dashboard CPU/Net charts: theme-neutral grid + themed labels (was harsh on dark).
- Settings: guidance to use the Black base theme with dark presets.

## 2026.07.24
- Initial scaffold.
- Buttons-loader injection (enabled/disabled), preset dropdown, custom CSS overrides.
- Presets: bebamu (Light/Dark), Nord, Dracula, Solarized Dark, Monokai, Gruvbox Dark.
- Runtime JS: Docker "update available" badge + tooltip, shadow-DOM style bridge.
"""


def cdata(text: str) -> str:
    # CDATA cannot contain the literal "]]>" — split it safely if present.
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def collect_files():
    files = []
    for root, _dirs, names in sorted(os.walk(SRC)):
        for fn in sorted(names):
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, SRC)
            with open(full, "r", encoding="utf-8") as fh:
                content = fh.read()
            files.append((rel.replace(os.sep, "/"), content))
    return files


INSTALL = f"""
# --- Unraid Themer: prepare directories ---
rm -rf {WEBROOT}
mkdir -p {WEBROOT}/presets {WEBROOT}/js
mkdir -p {FLASH}/presets
exit 0
""".strip()

# runs on install AND on every boot (plugin re-processed at array start)
BOOT = f"""
# --- Unraid Themer: restore user data from flash to webroot ---
# Config (SERVICE/PRESET) is read straight from flash by parse_plugin_cfg,
# merged over the shipped default.cfg — nothing to copy for it.

# User custom overrides live on flash; recreate the webroot copy nginx serves.
if [ ! -f {FLASH}/custom.css ]; then
    echo '/* Your custom CSS overrides — loaded on top of the selected preset. */' > {FLASH}/custom.css
fi
cp -f {FLASH}/custom.css {WEBROOT}/custom.css 2>/dev/null

# Let users drop extra presets on the flash; mirror them into the webroot too.
if [ -d {FLASH}/presets ]; then
    cp -f {FLASH}/presets/*.css {WEBROOT}/presets/ 2>/dev/null
fi

echo "----------------------------------------------------"
echo " Unraid Themer installed."
echo " Go to Settings > Utilities > Unraid Themer"
echo "----------------------------------------------------"
exit 0
""".strip()

REMOVE = f"""
# --- Unraid Themer: full cleanup ---
rm -rf {WEBROOT}
rm -rf {FLASH}
exit 0
""".strip()


def build():
    parts = []
    parts.append("<?xml version='1.0' standalone='yes'?>")
    parts.append("<!DOCTYPE PLUGIN [")
    for k in ("name", "author", "version", "launch", "pluginURL", "support"):
        parts.append(f'  <!ENTITY {k:9s} "{META[k]}">')
    parts.append("]>")
    parts.append(
        f'<PLUGIN name="&name;" author="&author;" version="&version;" '
        f'launch="&launch;" pluginURL="&pluginURL;" support="&support;" '
        f'min="{META["min"]}" icon="{META["icon"]}">'
    )
    parts.append("")
    parts.append("<CHANGES>\n" + CHANGES.strip() + "\n</CHANGES>")
    parts.append("")

    # 1) prepare dirs
    parts.append('<FILE Run="/bin/bash">')
    parts.append("<INLINE>\n" + INSTALL + "\n</INLINE>")
    parts.append("</FILE>")
    parts.append("")

    # 2) payload files (recreated in webroot on every boot)
    for rel, content in collect_files():
        parts.append(f'<FILE Name="{WEBROOT}/{rel}">')
        parts.append("<INLINE>\n" + cdata(content) + "\n</INLINE>")
        parts.append("</FILE>")
        parts.append("")

    # 3) boot/install restore
    parts.append('<FILE Run="/bin/bash">')
    parts.append("<INLINE>\n" + BOOT + "\n</INLINE>")
    parts.append("</FILE>")
    parts.append("")

    # 4) uninstall
    parts.append('<FILE Run="/bin/bash" Method="remove">')
    parts.append("<INLINE>\n" + REMOVE + "\n</INLINE>")
    parts.append("</FILE>")
    parts.append("")
    parts.append("</PLUGIN>")

    out = "\n".join(parts) + "\n"
    dest = os.path.join(REPO, "unraid-themer.plg")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(out)
    n = len(collect_files())
    print(f"Wrote {dest} ({n} embedded files, version {META['version']}).")


if __name__ == "__main__":
    build()
