#!/usr/bin/env python3
"""Render a dashboard screenshot for every theme in the registry and build the
gallery page docs/themes.html from them.

Run:  python3 scripts/render_previews.py            # render all, write the page
      python3 scripts/render_previews.py nord       # render only these themes
      python3 scripts/render_previews.py --html     # only build preview/build/*.html
      python3 scripts/render_previews.py --check    # CI: every theme has its images

preview/dashboard.html is a stand-in for the Unraid dashboard with made-up data.
It reads the same variables and selectors as the real webGui, so each theme file
is applied to it unchanged, on the Dynamix base the theme declares
(`themer-base:`; a theme for any base is shown light and dark). Google Chrome
takes the screenshot headless; Pillow writes the WebP files. The images are
committed, so CI only checks that none is missing.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugin/usr/local/emhttp/plugins/unraid.themer")
PREVIEW = os.path.join(ROOT, "preview")
BUILD = os.path.join(PREVIEW, "build")
OUT = os.path.join(ROOT, "docs/assets/themes")
PAGE = os.path.join(ROOT, "docs/themes.html")
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SIZE = (1512, 950)          # same frame as the landing page hero shot
THUMB_WIDTH = 760


def themes():
    with open(os.path.join(ROOT, "themes/index.json"), encoding="utf-8") as f:
        return json.load(f)["themes"]


def bases(css):
    """The Dynamix bases a theme is shown on: its themer-base, both for any."""
    m = re.search(r"themer-base:\s*(white|black)", css)
    return [m.group(1)] if m else ["white", "black"]


def variants(t):
    """[(base, image stem)] for one registry entry."""
    stem = t["file"][:-4]
    with open(os.path.join(ROOT, "themes", t["file"]), encoding="utf-8") as f:
        bs = bases(f.read())
    if len(bs) == 1:
        return [(bs[0], stem)]
    return [(b, f"{stem}-{'light' if b == 'white' else 'dark'}") for b in bs]


def icon(name):
    with open(os.path.join(PLUGIN, "icons/svg", f"{name}.svg"), encoding="utf-8") as f:
        svg = f.read()
    svg = re.sub(r'\s(width|height)="[^"]*"', "", svg, count=2)
    return svg.replace("<svg", '<svg class="i" aria-hidden="true"', 1)


def page_for(theme_file, base):
    """The dashboard with this theme applied, as one HTML string."""
    with open(os.path.join(PREVIEW, "dashboard.html"), encoding="utf-8") as f:
        src = f.read()
    links = [os.path.join(PLUGIN, "fonts.css"), os.path.join(PREVIEW, "base.css"),
             os.path.join(ROOT, "themes", theme_file)]
    css = "\n".join(f'<link rel="stylesheet" href="file://{p}">' for p in links)
    src = src.replace("{{base}}", base).replace("{{css}}", css)
    return re.sub(r"\{\{icon:([a-z0-9-]+)\}\}", lambda m: icon(m.group(1)), src)


def build_html(only):
    os.makedirs(BUILD, exist_ok=True)
    built = []
    for t in themes():
        if only and t["file"][:-4] not in only:
            continue
        for base, stem in variants(t):
            path = os.path.join(BUILD, f"{stem}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(page_for(t["file"], base))
            built.append((stem, path))
    return built


def screenshot(src, png):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--allow-file-access-from-files", "--force-device-scale-factor=1",
                    f"--window-size={SIZE[0]},{SIZE[1]}", f"--screenshot={png}", f"file://{src}"],
                   check=True, capture_output=True)


def render(only):
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="themer-shot-")
    try:
        for stem, src in build_html(only):
            png = os.path.join(tmp, f"{stem}.png")
            screenshot(src, png)
            img = Image.open(png).convert("RGB")
            img.save(os.path.join(OUT, f"{stem}.webp"), "WEBP", quality=82, method=6)
            h = round(img.height * THUMB_WIDTH / img.width)
            img.resize((THUMB_WIDTH, h), Image.LANCZOS).save(
                os.path.join(OUT, f"{stem}-{THUMB_WIDTH}.webp"), "WEBP", quality=80, method=6)
            print(f"  rendered {stem}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def mode_label(t):
    b = t.get("base", "black")
    return "Light + Dark" if b == "any" else ("Light" if b in ("white", "azure") else "Dark")


def write_page():
    cards = []
    for t in themes():
        vs = variants(t)
        shots = "".join(
            f'<a class="g__shot" href="assets/themes/{stem}.webp">'
            f'<img src="assets/themes/{stem}-{THUMB_WIDTH}.webp" width="{THUMB_WIDTH}" '
            f'height="{round(SIZE[1] * THUMB_WIDTH / SIZE[0])}" loading="lazy" '
            f'alt="Unraid dashboard with the {html.escape(t["name"])} theme'
            f'{", " + ("light" if base == "white" else "dark") if len(vs) > 1 else ""}"></a>'
            for base, stem in vs)
        swatch = "".join(f'<i style="background:{c}" title="{c}"></i>' for c in t.get("swatch", []))
        mode = mode_label(t)
        cards.append(
            f'    <li class="theme g__card{" g__card--pair" if len(vs) > 1 else ""}" data-mode="{"dark light" if mode == "Light + Dark" else mode.lower()}">\n'
            f'      <div class="g__shots{" g__shots--pair" if len(vs) > 1 else ""}">{shots}</div>\n'
            f'      <div class="theme__strip" aria-hidden="true">{swatch}</div>\n'
            f'      <p class="theme__name">{html.escape(t["name"])} <span class="theme__tag">{mode}</span></p>\n'
            f'      <p class="theme__desc">{html.escape(t["description"])}</p>\n'
            f'      <p class="g__by">by {html.escape(t.get("author", ""))} &middot; <a href="https://github.com/benjaminmue/unraid-themer/blob/main/themes/{html.escape(t["file"])}">{html.escape(t["file"])}</a></p>\n'
            f'    </li>')
    with open(os.path.join(PREVIEW, "themes.template.html"), encoding="utf-8") as f:
        tpl = f.read()
    out = tpl.replace("{{count}}", str(len(cards))).replace("{{cards}}", "\n".join(cards))
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"  wrote docs/themes.html ({len(cards)} themes)")


def check():
    """Warn, do not fail: a theme approved by the bot has no images until someone renders them."""
    missing = [f"{stem}.webp" for t in themes() for _, stem in variants(t)
               for suffix in ("", f"-{THUMB_WIDTH}")
               if not os.path.exists(os.path.join(OUT, f"{stem}{suffix}.webp"))]
    page = open(PAGE, encoding="utf-8").read() if os.path.exists(PAGE) else ""
    unlisted = [t["file"] for t in themes() if f'themes/{t["file"]}"' not in page]
    for m in sorted(set(missing)):
        print(f"::warning::no preview image for {m}; run scripts/render_previews.py")
    for u in unlisted:
        print(f"::warning::{u} is not in docs/themes.html; run scripts/render_previews.py")
    print(f"previews: {len(set(missing))} missing, {len(unlisted)} not on the page")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--check" in sys.argv:
        check()
    elif "--html" in sys.argv:
        for stem, path in build_html(args):
            print(path)
    else:
        render(args)
        write_page()


if __name__ == "__main__":
    main()
