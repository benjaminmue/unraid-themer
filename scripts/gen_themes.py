#!/usr/bin/env python3
"""
gen_themes.py — generate community theme CSS files + register them in
themes/index.json from a compact palette table. Each theme follows the same
Unraid-variable structure as the hand-written presets (dracula.css etc.), so
coverage stays consistent. Run from the repo root:  python3 scripts/gen_themes.py
"""
import os, json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES = os.path.join(REPO, "themes")

# name, slug, base(black/white), accent-text-on-button, overlay(rgb for translucent fills),
# palette: bg, bg2, surface, text, dim, border, accent, accent2 ; description
THEME_DATA = [
    # ---- aesthetic dark ----
    ("Everforest", "everforest", "black", "#2b3339", "255,255,255",
     ("#2b3339", "#323c41", "#3a454a", "#d3c6aa", "#9da9a0", "#4a555b", "#a7c080", "#e67e80"),
     "Warm forest green with soft retro contrast."),
    ("Kanagawa", "kanagawa", "black", "#1f1f28", "255,255,255",
     ("#1f1f28", "#2a2a37", "#363646", "#dcd7ba", "#c8c093", "#54546d", "#7e9cd8", "#e46876"),
     "Muted ink-wash blues inspired by Hokusai."),
    ("One Dark", "one-dark", "black", "#ffffff", "255,255,255",
     ("#282c34", "#2f343d", "#3b4048", "#abb2bf", "#7f848e", "#3e4451", "#61afef", "#c678dd"),
     "Atom's classic, balanced dark."),
    ("Ayu Mirage", "ayu-mirage", "black", "#1f2430", "255,255,255",
     ("#1f2430", "#232834", "#2d3441", "#cbccc6", "#8a9199", "#323945", "#ffcc66", "#73d0ff"),
     "Soft mirage blues with a warm amber accent."),
    ("Synthwave 84", "synthwave-84", "black", "#241b2f", "255,255,255",
     ("#241b2f", "#2a1f3d", "#34294f", "#f8f8f2", "#b6a2d3", "#463465", "#ff7edb", "#36f9f6"),
     "Neon '84 sunset: hot pink and electric cyan."),
    ("Matrix", "matrix", "black", "#001a00", "255,255,255",
     ("#0b0f0b", "#0f160f", "#122012", "#63f763", "#3ea63e", "#1c3a1c", "#00ff41", "#b6ff00"),
     "Green-on-black terminal. Wake up."),
    # ---- homage / fun ----
    ("Rick and Morty", "rick-and-morty", "black", "#08140f", "255,255,255",
     ("#0e1b16", "#12241d", "#163027", "#d7f5e3", "#8fc7a8", "#1f4536", "#97ce4c", "#24b0c9"),
     "Interdimensional portal green with lab cyan. Wubba lubba dub dub."),
    ("Unraid Appreciation", "unraid-appreciation", "black", "#1a1a1a", "255,255,255",
     ("#1a1a1a", "#212121", "#2a2a2a", "#f0f0f0", "#b0b0b0", "#333333", "#ff8c2f", "#e32929"),
     "A love letter to Lime Tech — Unraid orange to red on coal."),
    # ---- light homage ----
    ("SpongeBob", "spongebob", "white", "#3a3320", "0,0,0",
     ("#eaf6ff", "#d9efff", "#fff6c2", "#3a3320", "#7a6f3f", "#bfe3f5", "#f2b705", "#ff5a8a"),
     "Sunny sponge yellow, coral pink and ocean cyan. Bikini Bottom vibes."),
    ("Simpsons", "simpsons", "white", "#ffffff", "0,0,0",
     ("#fff8d6", "#fff1b0", "#fffbe6", "#2b2b2b", "#6b6b3a", "#e6d98a", "#d6001c", "#1a6fd6"),
     "Cartoon yellow with Duff red and Marge blue."),
]

TEMPLATE = """/* Unraid Themer preset: {name} — {description} */
:root {{
  /* ---------------- Palette ---------------- */
  --t-bg: {bg};
  --t-bg2: {bg2};
  --t-surface: {surface};
  --t-text: {text};
  --t-dim: {dim};
  --t-border: {border};
  --t-accent: {accent};
  --t-accent2: {accent2};

  /* ---------------- Dynamix core ---------------- */
  --text-color: var(--t-text);
  --alt-text-color: var(--t-dim);
  --link-text-color: var(--t-accent);

  --background-color: var(--t-bg);
  --mild-background-color: var(--t-bg2);

  --border-color: var(--t-border);
  --input-border-color: var(--t-border);
  --table-border-color: var(--t-border);
  --table-background-color: var(--t-bg2);
  --table-header-background-color: var(--t-surface);
  --hover-table-row-background-color: rgba({overlay}, 0.06);
  --hr-color: var(--t-border);
  --shade-bg-color: var(--t-surface);
  --focus-input-bg-color: var(--t-surface);

  --header-background-color: var(--t-surface);
  --header-text-color: var(--t-text);
  --header-text-primary: var(--t-text);
  --header-text-secondary: var(--t-dim);

  --title-header-background-color: var(--t-bg2);

  --footer-text: var(--t-text);
  --footer-background-color: var(--t-surface);

  --usage-bar-background-color: rgba({overlay}, 0.12);
  --usage-bar-used-background-color: var(--t-accent);
  --usage-disk-background-color: rgba({overlay}, 0.12);

  --button-text-color: {btn_text};
  --button-background: var(--t-accent);
  --button-border: 1px solid var(--t-accent);

  --scrollbar-color: rgba({overlay}, 0.3);
  --scrollbar-hover-color: var(--t-accent);
  --small-shadow: none;

  --dashboard-icon-color: var(--t-dim);

  /* ---------------- Brand remap (Unraid orange/blue -> preset accents) ---------------- */
  --orange-500: var(--t-accent);
  --orange-800: var(--t-accent2);
  --brand-orange: var(--t-accent);
  --brand-red: var(--t-accent2);
  --blue-700: var(--t-accent);
  --blue-800: var(--t-accent);

  /* ---------------- Unraid 7 UUI / shadcn web-component tokens ---------------- */
  --ui-bg: var(--t-bg);
  --ui-bg-muted: var(--t-bg2);
  --ui-bg-elevated: var(--t-surface);
  --ui-bg-accented: var(--t-surface);
  --ui-text: var(--t-text);
  --ui-text-muted: var(--t-dim);
  --ui-text-dimmed: var(--t-dim);
  --ui-text-highlighted: var(--t-text);
  --ui-border: var(--t-border);
  --ui-primary: var(--t-accent);
  --primary: var(--t-accent);
  --background: var(--t-bg);
  --foreground: var(--t-text);
  --card: var(--t-bg2);
  --popover: var(--t-bg2);
  --border: var(--t-border);
  --ring: var(--t-accent);
  --accent: var(--t-accent2);
}}

/* ==================== Elemente ==================== */
.button, button, input, select, textarea, .tabs label {{
  border-radius: 0 !important;
}}
input[type="button"], input[type="submit"], input[type="reset"], button,
.button:not(.apps):not(.vms):not(.compose-stacks) {{
  background: var(--t-accent) !important;
  color: {btn_text} !important;
  border: 1px solid var(--t-accent) !important;
  box-shadow: none !important;
}}

a.blue-text, .blue-text {{ color: var(--t-accent) !important; }}
#docker_view .blue-text {{ color: var(--t-accent2) !important; }}

#menu .nav-item.active a {{ color: var(--t-accent) !important; }}
#menu .nav-item.active:after {{ background: var(--t-accent) !important; }}

.greenbar {{ background: var(--usage-bar-used-background-color) !important; }}
.redbar {{ background: var(--t-accent2) !important; }}

div.title {{ border-left: 3px solid var(--t-accent); }}

table.dashboard tbody {{
  border: 1px solid var(--border-color) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}}
.tile-header-left {{ justify-content: flex-start !important; }}
.tile-header-main {{
  text-align: left !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 800;
}}
.tile-header-main::before {{
  content: "";
  display: inline-block;
  width: 3px;
  height: 0.95em;
  background: var(--t-accent);
  margin-right: 9px;
  vertical-align: -1px;
}}

/* ==================== compat: base-theme-driven surfaces ==================== */
:root {{
  --dynamix-tablesorter-tbody-row-bg-color: var(--table-background-color);
  --dynamix-tablesorter-tbody-row-alt-bg-color: var(--mild-background-color);
  --dynamix-tablesorter-tbody-row-border-color: var(--border-color);
  --dynamix-tablesorter-thead-th-bg-color: var(--table-header-background-color);
  --dynamix-tablesorter-thead-th-text-color: var(--text-color);
  --dynamix-tablesorter-thead-row-border-color: var(--border-color);
  --dynamix-select-bg-color: var(--table-background-color);
  --dynamix-box-text-color: var(--text-color);

  --template-background: var(--mild-background-color) !important;
  --template-hover-background: var(--shade-bg-color) !important;
  --ca-legacy-background-color: var(--background-color) !important;
  --sidebar-background: var(--mild-background-color) !important;
  --support-popup-background: var(--mild-background-color) !important;
  --ca-light-bg-color: var(--mild-background-color) !important;
  --ca-dark-text-color: var(--text-color) !important;
  --ca-medium-text-color: var(--alt-text-color) !important;
  --ca-light-text-color: var(--text-color) !important;
  --ca-lighter-text-color: var(--text-color) !important;
}}

/*! themer-base: {base} */
"""


def main():
    index_path = os.path.join(THEMES, "index.json")
    index = json.load(open(index_path, encoding="utf-8"))
    existing = {t["file"] for t in index["themes"]}

    added = 0
    for name, slug, base, btn_text, overlay, pal, desc in THEME_DATA:
        bg, bg2, surface, text, dim, border, accent, accent2 = pal
        css = TEMPLATE.format(name=name, description=desc, base=base, btn_text=btn_text,
                              overlay=overlay, bg=bg, bg2=bg2, surface=surface, text=text,
                              dim=dim, border=border, accent=accent, accent2=accent2)
        with open(os.path.join(THEMES, f"{slug}.css"), "w", encoding="utf-8") as fh:
            fh.write(css)
        entry = {"name": name, "file": f"{slug}.css", "author": "benjaminmue",
                 "base": base, "description": desc}
        if f"{slug}.css" not in existing:
            index["themes"].append(entry)
            added += 1
        else:  # refresh metadata of an existing entry
            for t in index["themes"]:
                if t["file"] == f"{slug}.css":
                    t.update(entry)
    json.dump(index, open(index_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(index_path, "a", encoding="utf-8").write("\n")
    print(f"Generated {len(THEME_DATA)} theme CSS files, added {added} new registry entries "
          f"({len(index['themes'])} total).")


if __name__ == "__main__":
    main()
