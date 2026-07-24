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
    "version": "2026.07.24v",
    "launch": "Settings/UnraidThemer",
    "pluginURL": "https://github.com/benjaminmue/unraid-themer/raw/refs/heads/main/unraid-themer.plg",
    "support": "https://github.com/benjaminmue/unraid-themer",
    "min": "7.0.0",
    "icon": "paint-brush",
}

CHANGES = """## Unraid Themer
## 2026.07.24v
- Header toolbar now themed properly: the bottom row (search, logout, terminal,
  file manager, feedback, info, log, help, language) uses Unraid's own icon font
  (icon-u-*) and is now mapped by the CSS icon set like everything else.
- The top-right notifications bell and account dropdown (Vue inline SVGs) are
  matched more reliably (accessible name incl. sr-only text) and swapped via JS.

## 2026.07.24u
- Header icons: best-effort swap of the whole Vue-header toolbar (search, logout,
  terminal, clone, feedback, remote, notifications bell, menu, help, ...) — which
  lives in an open shadow DOM unreachable by CSS — to match the active icon set,
  via a defensive shadow-DOM pass in themer.js. Only runs with an icon set active,
  matches buttons by their accessible name, and only replaces the SVG visual —
  no-ops on any miss, never touches handlers.

## 2026.07.24t
- Icon sets: three more bundled open-source sets — Tabler, Phosphor, Heroicons
  (in addition to Lucide). Pick one under "Icon set". Missing glyphs in a set
  fall back to Lucide so a set is always complete.
- Custom Icons: upload your own SVG file per slot (validated like pasted markup),
  next to the grid picker.

## 2026.07.24s
- Custom Icons: pick icons from a visual, searchable grid (like an emoji picker,
  but the actual Lucide icons) instead of a text-only dropdown. Each row has a
  "pick" button that opens the grid; the text field still accepts a name, https
  SVG URL or pasted SVG for anything custom.

## 2026.07.24r
- Custom Icons is now its own entry under Settings > Utilities ("Themer Icons")
  — the sub-tab under the main page did not render. The two pages cross-link.

## 2026.07.24q
- Custom Icons: new sub-page (Settings > Utilities > Unraid Themer > Custom
  Icons) listing every themeable icon slot with its reference icon and a live
  preview. Assign a custom icon per slot — a bundled Lucide name, a raw https
  SVG URL, or pasted SVG markup. Inputs are validated (no scripts, event
  handlers or external refs), stored on flash, and compiled into overrides.css
  that wins over the icon set (works even with set = Default).

## 2026.07.24p
- Icon set (Lucide): remap the remaining Docker-menu action glyphs — WebUI /
  Project Page (globe), Edit (wrench), Support (life-ring), Logs (list) and
  help — so the container context menu is fully Lucide.

## 2026.07.24o
- Icon set (Lucide): also swaps the Font Awesome action glyphs used on the
  Docker / VM / tile toolbars (play, stop, pause, restart, power, cog, trash,
  terminal, download, chevrons, ...) so the whole UI uses one line-icon set.

## 2026.07.24n
- Icon set (v1): optional "Lucide" set swaps Unraid's UI glyphs (docker, cpu,
  disks, fan, ...) for open-source line icons that tint with the theme, via
  CSS mask. Pick it under "Icon set"; "Default" keeps Unraid's icons.

## 2026.07.24m
- Only bebamu is now built-in; the other default themes are seeded to flash on
  first install, so they can be uninstalled from the store like any added theme
  (and stay removed).

## 2026.07.24l
- Store: user-added themes now show an "Uninstall" button (built-in stay
  "Installed"). The separate "Added themes" row now only lists URL imports
  that aren't in the store.

## 2026.07.24k
- Move the "Added themes" (remove) section down next to the theme store, so
  all theme management is grouped together.

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
mkdir -p {WEBROOT}/presets {WEBROOT}/js {WEBROOT}/defaults {WEBROOT}/overrides
mkdir -p {FLASH}/presets {FLASH}/overrides
exit 0
""".strip()

# runs on install AND on every boot (plugin re-processed at array start)
BOOT = f"""
# --- Unraid Themer: restore user data from flash to webroot ---
# Config (SERVICE/PRESET) is read straight from flash by parse_plugin_cfg,
# merged over the shipped default.cfg — nothing to copy for it.

# Seed the default themes onto flash ONCE (first install). After that they are
# user-removable and won't come back. Only bebamu is built-in (from the .plg).
if [ ! -f {FLASH}/presets/.seeded ]; then
    cp -n {WEBROOT}/defaults/*.css {FLASH}/presets/ 2>/dev/null
    touch {FLASH}/presets/.seeded
fi

# User custom overrides live on flash; recreate the webroot copy nginx serves.
if [ ! -f {FLASH}/custom.css ]; then
    echo '/* Your custom CSS overrides — loaded on top of the selected preset. */' > {FLASH}/custom.css
fi
cp -f {FLASH}/custom.css {WEBROOT}/custom.css 2>/dev/null

# Activate every flash theme (seeded defaults + imports) in the webroot nginx serves.
cp -f {FLASH}/presets/*.css {WEBROOT}/presets/ 2>/dev/null

# Per-icon overrides (custom SVGs + generated overrides.css) live on flash; restore them.
mkdir -p {WEBROOT}/overrides
cp -f {FLASH}/overrides/*.svg {WEBROOT}/overrides/ 2>/dev/null
cp -f {FLASH}/overrides.css {WEBROOT}/overrides.css 2>/dev/null

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
