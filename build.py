#!/usr/bin/env python3
"""
build.py — assemble the inline unraid-themer.plg from the source tree.

The plugin is fully self-contained (no .txz, no external assets): every file
under plugin/usr/local/emhttp/plugins/unraid.themer/ is embedded into the .plg
as a CDATA <FILE> block. Unraid re-runs the .plg on every boot, which recreates
these files in the RAM webroot. User data (config + custom.css) lives on the
flash and is restored to the webroot by the boot script.

Release channels: the branch a .plg is built from becomes its channel. The
pluginURL and the theme-store registry URL both point at that branch, so an
installed beta keeps updating from beta and never crosses over to stable.
Versions must increase LEXICOGRAPHICALLY (Unraid compares them as strings);
beta builds use a "bNN" suffix, which sorts after every digit suffix of the
same date, so a stable release needs a newer date to supersede a beta.

Usage:  python3 build.py [--channel main|beta]
Output: ./unraid-themer.plg
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
NAME = "unraid.themer"
SRC = os.path.join(REPO, "plugin", "usr", "local", "emhttp", "plugins", NAME)
WEBROOT = f"/usr/local/emhttp/plugins/{NAME}"
FLASH = f"/boot/config/plugins/{NAME}"

# version per channel — a beta build must never claim a stable version number
VERSIONS = {
    "main": "2026.07.26.07",
    "beta": "2026.08.16.b05",
}


def current_channel():
    """--channel wins, otherwise the checked-out git branch, otherwise main."""
    if "--channel" in sys.argv:
        return sys.argv[sys.argv.index("--channel") + 1]
    try:
        branch = subprocess.run(["git", "-C", REPO, "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "main"
    return branch if branch in VERSIONS else "main"


CHANNEL = current_channel()
BASE_URL = f"https://github.com/benjaminmue/unraid-themer/raw/refs/heads/{CHANNEL}"

META = {
    "name": NAME,
    "author": "benjaminmue",
    "version": VERSIONS[CHANNEL],
    "launch": "Settings/UnraidThemer",
    "pluginURL": f"{BASE_URL}/unraid-themer.plg",
    "support": "https://github.com/benjaminmue/unraid-themer",
    "min": "7.0.0",
    "icon": "paint-brush",
}

CHANGES = """## Unraid Themer
## 2026.08.16.b05 (beta)
- Fixed unreadable buttons in 11 bundled themes. Filled buttons use the accent
  as their background, but the label was hard-coded white — on Nord, Dracula,
  Catppuccin Mocha, Tokyo Night, One Dark and Gruvbox that is a contrast ratio
  around 2:1, far below the WCAG AA minimum of 4.5. Labels now use the theme's
  own background while that clears AA, otherwise black or white, whichever the
  accent tolerates. All 20 store themes pass, and CI keeps them passing.
- The theme builder shows live WCAG contrast for the five pairs that carry text
  (body, muted, links, text on surface, button label), and picks the button
  label colour for you by the same rule instead of always writing white.

## 2026.08.16.b04 (beta)
- Reset a SINGLE icon: every slot gets an eraser button that clears just that
  one back to the icon-set default. Until now the only way back was "Reset all",
  which wiped every override.
- The slot table scrolls in its own box, so the column headers actually stay
  visible. A page-level sticky head did nothing because Unraid scrolls a
  container the plugin does not control.
- An empty filter result now says so instead of showing a blank table.

## 2026.08.16.b03 (beta)
- Themer Icons is usable again with 149 slots: a sticky filter bar with a search
  box (matches the label, the slot key and the set's default icon name), a
  category filter and an "Only customised" toggle, plus a counter. Category
  headings hide themselves when nothing under them matches, and the table head
  stays put while you scroll. The bar sits outside the form on purpose, so
  searching does not arm the Apply button.

## 2026.08.16.b02 (beta)
- Store rows line up again: the three button states (Get / Uninstall /
  Installed) have different label widths, which pushed every row's swatch and
  name to a different position. The row is a fixed-column grid now.
- Swatch chips get a hairline between them and a stronger outline, so a dark
  theme's background and surface no longer merge into one block on a dark base.

## 2026.08.16.b01 (beta)
- Theme store and preset dropdown now show each theme's palette as a colour
  strip, so you can see what a theme looks like before downloading it. Store
  entries carry their swatch in the registry; locally installed presets are
  parsed on the fly, which also covers themes you imported yourself.
- Beta channel: this build updates from the beta branch and reads the beta
  theme registry. The stable plugin in Community Applications is unaffected.

## 2026.07.26.07
- New: replace the Unraid wordmark (top-left) with your own logo, by URL (cached
  locally) or a file on the server via Unraid's file browser. Survives reboots;
  clear the field and Apply to restore the Unraid logo.

## 2026.07.26.06
- New: set a background image behind the whole UI. Add it by URL (downloaded and
  cached locally, so it is CSP-safe and works offline) or pick a file on the
  server with Unraid's file browser. A Dim slider keeps text readable, and it
  survives reboots. Clear the field and Apply to remove it.

## 2026.07.26.05
- Fix the Themer Icons Apply hanging forever and saving nothing: the form used
  multipart/form-data (for SVG upload), which Unraid's AJAX form submit cannot
  send, so the request stalled. The form is now a normal POST; uploading an SVG
  reads it in the browser and drops its markup into the field (the server already
  accepts pasted <svg>). Picking, typing and uploading now all save correctly.

## 2026.07.26.04
- Fix the Apply button staying greyed out on the Themer Icons page after picking
  an icon from the grid or uploading an SVG: those set the field from script,
  which fired no change event, so Unraid never armed Apply. It now enables on any
  edit (pick, upload or typing).

## 2026.07.26.03
- Fixed the broken grid glyph on the Themer Icons page title. It used a
  Font Awesome 4 name (picture-o) that no longer exists in Unraid 7, so the
  font drew a placeholder. Now uses a valid icon that also tints with the set.

## 2026.07.26.02
- Themer Icons page now exposes every icon the sets cover: 149 slots (was ~47)
  across Navigation, System, Settings pages, Toolbar (new UI, icon-u-*) and
  Actions. You can now override the Settings-page glyphs and the Vue header /
  toolbar icons individually, not just the System and action icons.

## 2026.07.26.01
- Added Comic Neue to the bundled fonts (a free, OFL-licensed Comic Sans-alike;
  the proprietary Comic Sans MS cannot be shipped). Pick it in the theme builder
  Font field; it falls back to a locally installed Comic Sans MS if you have one.

## 2026.07.26
- Fix updates getting stuck: Unraid compares plugin versions as plain strings,
  so 2026.07.25.10 / .11 sorted BEFORE .8 / .9 ('1' < '8') and were never
  offered. Bumped to a date that always sorts newer; future versions stay
  lexicographically increasing. Includes the bundled fonts (.11) and everything
  since .8.

## 2026.07.25.11
- Bundled webfonts: Inter, Roboto, Source Sans 3, JetBrains Mono and Nunito
  (open license, served locally). Pick one in the theme builder Font field and
  it is baked into your theme, working on any device.

## 2026.07.25.10
- Fix the version not showing on the settings page: it is now embedded at build
  time and read from the plugin folder (the old lookup path was unreliable).

## 2026.07.25.9
- Settings page tidy-up: narrower hex fields in the theme builder and a
  left-aligned, less-centered layout (page-scoped, other pages unchanged).

## 2026.07.25.8
- Docker "update available" badge: replace the (unreliable) native title with a
  proper styled hover tooltip, so hovering the ? actually explains it.

## 2026.07.25.7
- Fix the theme builder not initialising from the current theme (and live preview
  not working): its inline script was being mangled by the page's markdown pass.
  Moved it to an external file (js/themer-build.js).

## 2026.07.25.6
- Theme builder: the color pickers now start from your CURRENT running theme, so
  you tweak from where you are instead of a generic default. Added an optional
  Font field (a font-family stack) with live preview.
- Guided GitHub issue forms (bug report, feature request, submit a theme) linked
  from the settings page; submitted theme CSS is auto-validated by a bot before a
  human reviews it.

## 2026.07.25.5
- Theme builder (color picker): pick 8 colors — with a swatch or by typing
  #rrggbb / rgb(r,g,b) — see them preview live on the page, then Build+Apply
  to save them as a preset and switch to it. Like the old pre-7.2 theme editor.
- The alternative icon sets now also cover the newly-mapped Settings/nav/toolbar
  icons (Iconoir/Remix/Bootstrap/Carbon/Material natively; the others fall back
  to Lucide), so switching sets stays consistent across the whole UI.

## 2026.07.25.4
- Much wider icon coverage: mapped ~98 more Unraid glyphs (Settings/nav icons —
  dashboard, network, security, scheduler, shares, plugins, ... — and the
  icon-u-* toolbar/sort glyphs) so the Lucide set now themes the whole UI, not
  just the dashboard.
- Settings page: shows the installed version and adds GitHub, "Report an issue"
  and "Request a theme / feature" links.
- New theme guide (THEMES.md) + annotated sample (themes/_template.css); the
  settings page links to both.

## 2026.07.25.3
- Removed the SpongeBob icon set and the SpongeBob / Simpsons / Rick and Morty
  store themes.

## 2026.07.25.2
- New "SpongeBob" icon set — an under-the-sea joke set: Docker becomes a whale,
  the dashboard a pineapple, the fan a starfish, CPU a coral, users a jellyfish,
  shares a treasure chest, and so on. Sea motifs from game-icons.net (CC BY 3.0);
  slots without a sea equivalent fall back to Lucide. Pairs with the SpongeBob
  store theme. Pick it under "Icon set".

## 2026.07.25.1
- Fix the Custom Icons page showing its JavaScript as raw text: Unraid runs the
  page through markdown, which split the multi-line inline script on its blank
  lines. Moved the page JS to an external file (js/themer-icons.js); config is
  passed via data-* attributes. The icon grid picker works again.

## 2026.07.25
- Fix updates not being offered: PHP version_compare() treats letter suffixes
  like "z"/"aa"/"ab" as equal, so the update check never saw them as newer.
  Switched to a numeric date scheme (2026.07.25, then .1, .2, ...) that always
  compares correctly. Contains everything from 24aa/24ab.
- Fix nginx error-log spam: the header bell/menu swap tried a non-existent
  per-set path (icons/svg/lucide/bell.svg) before falling back; it now loads the
  flat icon directly, with in-flight de-duplication.

## 2026.07.24ab
- Five more bundled icon sets: Iconoir, Remix, Bootstrap, Carbon and Material
  Symbols (fetched via the Iconify API in the generator, missing glyphs fall
  back to Lucide). Nine sets total now — all appear in the "Icon set" dropdown
  and, grouped, in the per-slot grid picker. The picker discovers sets
  automatically from the bundled folders.

## 2026.07.24aa
- Custom Icons: the grid picker now shows ALL bundled sets (Lucide, Tabler,
  Phosphor, Heroicons), grouped and searchable — pick e.g. "tabler/cpu" for any
  slot. The main settings page gets a prominent "Open Themer Icons" button.

## 2026.07.24z
- Sidebar polish (Azure / Gray): the top header band now matches the content
  background (was a lighter gray), and the active/hover nav item uses a subtle
  preset-aware accent (flat tint + left accent bar) instead of the stock loud
  red-orange gradient. Preset-agnostic layout.css, no-op on top-nav layouts.

## 2026.07.24y
- Sidebar layouts (Azure / Gray) supported: the base pairing now keeps your
  layout family — on Azure/Gray a dark preset pairs to Gray and a light one to
  Azure, instead of switching you to the top-nav Black/White. bebamu's dark
  rules now also apply on the Gray base. (Azure/Gray share the same CSS
  variables as White/Black, so preset colors already carry over.)

## 2026.07.24x
- Custom Icons page: the per-row grid + upload buttons now show their glyphs
  (were blank on Unraid's button styling) — styled as subtle icon buttons.
- Header swap keeps the original icon's sizing class, so swapped bell/menu
  icons always render at the right size.

## 2026.07.24w
- Header bell/menu swap is more robust: the Vue header mounts async from ES
  modules, so retry over a longer window and on DOM mutations until both the
  notifications bell and the account menu are swapped, then stop.

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
            # the source tree is channel-agnostic; stamp the branch at build time
            content = content.replace("@CHANNEL@", CHANNEL)
            files.append((rel.replace(os.sep, "/"), content))
    return files


INSTALL = f"""
# --- Unraid Themer: prepare directories ---
rm -rf {WEBROOT}
mkdir -p {WEBROOT}/presets {WEBROOT}/js {WEBROOT}/defaults {WEBROOT}/overrides {WEBROOT}/bg {WEBROOT}/logo
mkdir -p {FLASH}/presets {FLASH}/overrides {FLASH}/bg {FLASH}/logo
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

# Background image + custom logo (URL cached or a picked file) live on flash; restore.
mkdir -p {WEBROOT}/bg {WEBROOT}/logo
cp -f {FLASH}/bg/* {WEBROOT}/bg/ 2>/dev/null
cp -f {FLASH}/logo/* {WEBROOT}/logo/ 2>/dev/null

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
    # embed the version as a plain file so the settings page can display it
    # regardless of where Unraid stores the installed .plg
    with open(os.path.join(SRC, "version"), "w", encoding="utf-8") as fh:
        fh.write(META["version"] + "\n")

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
    # CHANGES is plain text inside an XML element (not CDATA), so escape XML
    # metacharacters — otherwise a literal &, < or > breaks the .plg.
    changes_xml = (CHANGES.strip().replace("&", "&amp;")
                   .replace("<", "&lt;").replace(">", "&gt;"))
    parts.append("<CHANGES>\n" + changes_xml + "\n</CHANGES>")
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
