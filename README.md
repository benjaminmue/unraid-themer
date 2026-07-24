# Unraid Themer

A generic theming plugin for the **Unraid 7** webGUI. Pick a preset (or write your
own CSS), flip it on, and the whole interface restyles — the classic Dynamix pages
**and** the new Vue web-components — through Unraid's own CSS custom properties.

A modern, minimal successor in spirit to the discontinued *Theme Engine*, built on
the same injection mechanism the community's *Custom WebUI CSS* plugin uses, but
wrapped in a preset system instead of a raw textarea.

> ⚠️ **Work in progress.** This is an early scaffold. It has not yet been installed
> or verified on real hardware. Don't run it on a production server yet.

## Presets

| Preset | Look |
|---|---|
| **bebamu** | Editorial: cream paper / black hairlines / red signal. Ships a **Light + Dark** pair. |
| **Nord** | Arctic blue-grey, frost accents |
| **Dracula** | Dark with purple/pink accents |
| **Solarized Dark** | Deep teal base, blue/cyan accents |
| **Monokai** | Classic dark, magenta/green accents |
| **Gruvbox Dark** | Warm retro, orange/yellow accents |

All presets remap only *aesthetic* colors. **Semantic status colors** (disk health,
array state, warnings) are deliberately left untouched so the UI still means what it says.

## How it works

Unraid 7 has no global CSS hook, but a `.page` file with `Menu="Buttons"` is executed
by `DefaultPageLayout.php` inside `<head>` on **every** page. Unraid Themer uses that:

- **`UnraidThemerLoader.page`** (`Menu="Buttons:100"`) injects `<link>`s for the active
  preset + your custom overrides, plus a deferred `<script>`, only when enabled.
- **`UnraidThemer.page`** (`Menu="Utilities"`) is the settings screen (enable, preset,
  custom CSS).
- Presets restyle via `:root` **custom-property overrides**. These inherit through the
  open shadow DOM of the Vue web-components, so `--header-*`, `--ui-*` and the shadcn
  tokens recolor the new UI too — no `::part()` needed.
- **`js/themer.js`** does the things CSS can't: a Docker *"update available"* badge with a
  tooltip, and a bridge to push selector-based CSS into component shadow roots.

Config lives on the flash (`/boot/config/plugins/unraid.themer/`) and is mirrored to the
RAM webroot on boot, so it survives reboots.

## Install

Not released yet. Once published, install by pasting the raw `.plg` URL into
**Plugins → Install Plugin**:

```
https://github.com/benjaminmue/unraid-themer/raw/refs/heads/main/unraid-themer.plg
```

Then open **Settings → Utilities → Unraid Themer**, set *Enable* to **Yes**, pick a
preset, **Apply**, and hard-reload the browser.

For the bebamu Light/Dark pair, switch the base theme at **Settings → Display →
Dynamix color theme** (White = Light, Black = Dark).

## Add your own preset

Drop a `<name>.css` into `/boot/config/plugins/unraid.themer/presets/` — it appears in
the dropdown. A preset is just a stylesheet that overrides Unraid's variables; copy an
existing one as a template.

## Development

The `.plg` is fully self-contained (no external assets) and **generated** from the
source tree:

```
plugin/usr/local/emhttp/plugins/unraid.themer/   # source of every embedded file
  ├── UnraidThemer.page          # settings page (Menu=Utilities)
  ├── UnraidThemerLoader.page     # head injector (Menu=Buttons)
  ├── default.cfg                 # shipped defaults
  ├── js/themer.js                # runtime helper
  └── presets/*.css               # the themes

python3 build.py                  # regenerates unraid-themer.plg
```

Edit the source files, run `python3 build.py`, commit the regenerated `.plg`.

## Roadmap

- [ ] Verify on real hardware (Unraid 7.3.x)
- [ ] Live preview in the settings page
- [ ] Icon switcher — swap Unraid's UI icons (docker/cpu/disk…) for open-source sets
      (Lucide / Tabler) via CSS `mask` (auto-tinting), custom per icon
- [ ] Import/export presets (ZIP/URL)
- [ ] Optional bundled fonts (Inter) and background-image assets
- [ ] Community Applications submission

## Credits & prior art

- Injection mechanism modeled on [WuSiYu/unraid-custom-css](https://github.com/WuSiYu/unraid-custom-css).
- Preset/plugin structure informed by [Skitals/unraid-theme-engine](https://github.com/Skitals/unraid-theme-engine) (discontinued).
- Classic palettes: Nord, Dracula, Solarized, Monokai, Gruvbox (respective communities).

## Transparency

Built with heavy AI assistance (Claude Code). Reviewed and maintained by
[@benjaminmue](https://github.com/benjaminmue).

## Icon set credits

The bundled icon sets are open source, each under its own license:

- **Lucide** (ISC), **Tabler** (MIT), **Phosphor** (MIT), **Heroicons** (MIT),
  **Iconoir** (MIT), **Bootstrap Icons** (MIT)
- **Remix Icon**, **Carbon**, **Material Symbols** (Apache-2.0)
- **SpongeBob** (under-the-sea joke set) uses icons from
  [game-icons.net](https://game-icons.net) — **CC BY 3.0**

The plugin's own code is MIT. Icon glyphs remain under their respective licenses.

## License

MIT — see [LICENSE](LICENSE).
