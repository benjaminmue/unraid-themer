# Unraid Themer

A generic theming plugin for the **Unraid 7** webGUI. Pick a theme (or build your
own), flip it on, and the whole interface restyles — the classic Dynamix pages
**and** the new Vue web-components — through Unraid's own CSS custom properties.
Swap the UI icons for open-source icon sets, or override individual icons.

A modern, minimal successor in spirit to the discontinued *Theme Engine*, wrapped
in a theme + icon system instead of a raw CSS textarea.

> 🤖 **Built with AI.** This plugin was written largely by an AI assistant
> (Claude Code / Anthropic), directed, reviewed and tested on real hardware by
> [@benjaminmue](https://github.com/benjaminmue). It runs on his own Unraid 7.3
> server. Read the code before trusting it on yours — issues and PRs welcome.

## Features

- **Themes** — bundled presets plus a built-in **theme store** you can browse and
  download from on demand. 19+ community themes and counting.
- **Icon sets** — swap Unraid's UI glyphs for **9 open-source line sets**
  (Lucide, Tabler, Phosphor, Heroicons, Iconoir, Remix, Bootstrap, Carbon,
  Material Symbols) that tint with the theme. Or set **any individual icon** from
  a grid picker, an SVG URL, or your own uploaded SVG.
- **Whole-UI coverage** — classic Dynamix pages, the Vue header (bell, menu,
  toolbar), Community Apps, tables, dashboard and the Settings icons.
- **Sidebar layouts** — Azure / Gray are supported; the base pairing keeps you in
  your layout family.
- **Non-destructive** — disable it and the webGUI is 100% stock. Semantic status
  colors (disk health, array state) are deliberately left untouched.
- **Self-contained** — one `.plg`, no external runtime dependencies.

## Install

**Plugins → Install Plugin**, paste:

```
https://github.com/benjaminmue/unraid-themer/raw/refs/heads/main/unraid-themer.plg
```

Then open **Settings → Utilities → Unraid Themer**, set *Enable* to **Yes**, pick a
theme, **Apply**, and hard-reload the browser (Cmd/Ctrl+Shift+R).

## Themes

Bundled and store themes appear in the **Theme preset** dropdown; the **Theme store**
downloads more on demand (search + light/dark filter, validated before saving). On
**Apply** the plugin pairs the Dynamix base (dark themes → Black/Gray, light → White/
Azure) so the Vue components and Community Apps render in the right mode.

**Make your own:** see [THEMES.md](THEMES.md) and the annotated
[`themes/_template.css`](themes/_template.css). It's mostly 8 colors. Submit one with
a PR to [`themes/`](themes/) — a GitHub Action validates every theme before it can be
listed in the store.

## Icons

**Icon set** swaps every UI glyph for one open-source set. For finer control, the
**Themer Icons** page lists every slot with a live preview — pick from a searchable
grid of all bundled sets, paste an SVG URL, or upload your own SVG (all validated).

## How it works

Unraid 7 has no global CSS hook, but a `.page` with `Menu="Buttons"` runs inside
`<head>` on every page. Unraid Themer uses that to inject the active theme + icon set
+ your overrides, only when enabled. Themes restyle via `:root` custom-property
overrides, which inherit through the open shadow DOM of the Vue web-components, so the
new UI recolors too. `js/themer.js` handles what CSS can't (the Vue header bell/menu
icon swap, a Docker "update available" badge, dashboard chart colors). Config lives on
the flash and is mirrored to the RAM webroot on boot, so it survives reboots.

## Development

The `.plg` is fully self-contained and **generated** from the source tree:

```
plugin/usr/local/emhttp/plugins/unraid.themer/   # every embedded file
scripts/gen_iconsets.py                           # build the alt icon sets
scripts/gen_themes.py                             # build community themes
python3 build.py                                  # regenerate unraid-themer.plg
```

Edit source, run `python3 build.py`, commit the regenerated `.plg`.

## Credits & prior art

This plugin was **inspired by** two prior community projects, which showed what's
possible and how to hook into the webGUI:

- [**WuSiYu/unraid-custom-css**](https://github.com/WuSiYu/unraid-custom-css) — the
  CSS-injection mechanism (a `Menu="Buttons"` `.page` running in `<head>`).
- [**Skitals/unraid-theme-engine**](https://github.com/Skitals/unraid-theme-engine)
  (discontinued) — the theme-engine / plugin structure.

Thanks to both authors. Classic palettes come from their respective communities:
Nord, Dracula, Solarized, Monokai, Gruvbox, Everforest, Kanagawa, Catppuccin,
Tokyo Night, One Dark, Ayu.

### Icon set licenses

The bundled icon sets are open source, each under its own license:

- **Lucide** (ISC); **Tabler**, **Phosphor**, **Heroicons**, **Iconoir**,
  **Bootstrap Icons** (MIT); **Remix Icon**, **Carbon**, **Material Symbols** (Apache-2.0).

### Bundled fonts

Optional webfonts you can pick in the theme builder, served locally:

- **Inter**, **Source Sans 3**, **JetBrains Mono**, **Nunito** — SIL Open Font License
- **Roboto** — Apache-2.0

The plugin's own code is MIT. Icon glyphs and fonts remain under their respective licenses.

## License

MIT — see [LICENSE](LICENSE).
