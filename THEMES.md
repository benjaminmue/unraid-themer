# Making a theme for Unraid Themer

A theme is a single CSS file that overrides Unraid's CSS custom properties.
Unraid's whole webGUI is driven by those properties, so in most cases you only
change **8 palette colors** and everything follows.

## Quick start

1. Copy [`themes/_template.css`](themes/_template.css) and rename it in
   kebab-case, e.g. `my-theme.css`.
2. Edit the 8 colors in the `PALETTE` block at the top.
3. Set the base marker on the **last line** (`black` for a dark theme, `white`
   for a light one).
4. Drop the file into `/boot/config/plugins/unraid.themer/presets/` on your
   server, then **Settings → Utilities → Unraid Themer → Theme preset →** pick it
   → **Apply**.

That's it. Reload the browser (Cmd/Ctrl+Shift+R) to see changes.

## The 8 palette colors

| Variable | What it is |
|---|---|
| `--t-bg` | page background |
| `--t-bg2` | cards, tables, mild surfaces |
| `--t-surface` | header bar, elevated surfaces |
| `--t-text` | main text |
| `--t-dim` | secondary / muted text |
| `--t-border` | borders and hairlines |
| `--t-accent` | primary accent — links, active nav, buttons, usage bars |
| `--t-accent2` | secondary accent — Docker "update available", the red bar |

Everything else in the template is already wired to these, including the Unraid 7
Vue web-components (notifications panel, Connect) via the `--ui-*` / shadcn tokens.

## The base marker (required)

The last line of every theme declares which Dynamix base it pairs with, so the
web-components and Community Apps render in the right light/dark mode:

```css
/*! themer-base: black */   /* dark theme  */
/*! themer-base: white */   /* light theme */
```

On **Apply**, the plugin switches the Dynamix base to match — and keeps your
layout family (if you're on the Azure/Gray sidebar layout it pairs to Gray/Azure
instead of Black/White).

## Light themes

For a light theme, set `themer-base: white` **and** change the translucent fills
from `rgba(255,255,255, …)` to `rgba(0,0,0, …)` (usage bars, hover rows,
scrollbar) so the overlays stay subtle on a light background. Use a dark
`--button-text-color` if your accent is light.

## Tips

- Don't restyle semantic status colors (disk health green, array-stopped red) —
  they carry meaning and every built-in theme leaves them alone.
- Keep contrast readable: `--t-text` on `--t-bg`, and `--button-text-color` on
  `--t-accent`.
- Prefer overriding variables over adding element rules; the `Elemente` block in
  the template is optional flair you can trim.

## Sharing your theme

- **Just for you:** keep it in `presets/` on your flash (above). It shows in the
  preset dropdown and survives reboots.
- **In the community store:** open a PR that adds your `my-theme.css` to
  [`themes/`](themes/) and an entry to [`themes/index.json`](themes/index.json):

  ```json
  { "name": "My Theme", "file": "my-theme.css", "author": "you",
    "base": "black", "description": "Short one-liner.",
    "swatch": ["#1a1b26", "#24283b", "#c0caf5", "#7aa2f7", "#bb9af7"] }
  ```

  You do not have to write `swatch` by hand — run
  `python3 scripts/gen_swatches.py` and it reads the palette straight out of your
  CSS (background, surface, text, accent, accent 2). The store shows it as a
  colour strip so people see your theme before downloading it. CI checks that
  every entry has a current swatch.

  A GitHub Action ([`scripts/sanitize_css.py`](scripts/sanitize_css.py)) validates
  every submitted theme (no scripts, `javascript:`, `@import` or external
  `url()`), so themes stay safe to download. Once merged it appears in everyone's
  **Theme store** on demand.
