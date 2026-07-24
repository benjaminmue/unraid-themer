#!/usr/bin/env python3
"""
gen_iconsets.py — generate alternative icon sets (Tabler, Phosphor, Heroicons)
from the Lucide baseline. For every icon slot in lucide.css we fetch the set's
equivalent SVG; if a name is missing we fall back to the bundled Lucide SVG, so
a set is always complete (never a broken icon). Outputs icons/<set>.css plus the
fetched SVGs under icons/svg/<set>/. Run from the repo root:  python3 scripts/gen_iconsets.py
"""
import os, re, sys, urllib.request

ICONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "plugin", "usr", "local", "emhttp", "plugins", "unraid.themer", "icons")
WEBURL = "/plugins/unraid.themer/icons"

SETS = {
    "tabler":    "https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{}.svg",
    "phosphor":  "https://raw.githubusercontent.com/phosphor-icons/core/main/assets/regular/{}.svg",
    "heroicons": "https://raw.githubusercontent.com/tailwindlabs/heroicons/master/optimized/24/outline/{}.svg",
}

# lucide stem -> candidate name in each set (first that resolves wins; else Lucide fallback)
MAP = {
    # stem:            tabler,                 phosphor,            heroicons
    "gauge":          ("gauge",                "gauge",             "chart-bar-square"),
    "circuit-board":  ("cpu-2",                "circuitry",         "cpu-chip"),
    "cpu":            ("cpu",                  "cpu",               "cpu-chip"),
    "memory-stick":   ("device-sd-card",       "memory",            "server-stack"),
    "ethernet-port":  ("network",              "network",           "signal"),
    "battery-charging":("battery-charging",    "battery-charging",  "bolt"),
    "fan":            ("propeller",            "fan",               "arrow-path-rounded-square"),
    "container":      ("brand-docker",         "cube",              "cube"),
    "monitor":        ("device-desktop",       "desktop",           "computer-desktop"),
    "folder":         ("folder",               "folder",            "folder"),
    "users":          ("users",                "users",             "users"),
    "user":           ("user",                 "user",              "user"),
    "hard-drive":     ("server-2",             "hard-drives",       "circle-stack"),
    "disc":           ("disc",                 "disc",              "record"),
    "activity":       ("activity-heartbeat",   "pulse",             "heart"),
    "server":         ("server",               "server",            "server"),
    "play":           ("player-play",          "play",              "play"),
    "square":         ("player-stop",          "stop",              "stop"),
    "pause":          ("player-pause",         "pause",             "pause"),
    "refresh-cw":     ("refresh",              "arrows-clockwise",  "arrow-path"),
    "rotate-cw":      ("rotate-clockwise",     "arrow-clockwise",   "arrow-path"),
    "power":          ("power",                "power",             "power"),
    "settings":       ("settings",             "gear",              "cog-6-tooth"),
    "trash-2":        ("trash",                "trash",             "trash"),
    "terminal":       ("terminal-2",           "terminal",          "command-line"),
    "download":       ("download",             "download-simple",   "arrow-down-tray"),
    "cloud-download": ("cloud-download",       "cloud-arrow-down",  "cloud-arrow-down"),
    "menu":           ("menu-2",               "list",              "bars-3"),
    "plus":           ("plus",                 "plus",              "plus"),
    "chevron-up":     ("chevron-up",           "caret-up",          "chevron-up"),
    "chevron-down":   ("chevron-down",         "caret-down",        "chevron-down"),
    "search":         ("search",               "magnifying-glass",  "magnifying-glass"),
    "x":              ("x",                    "x",                 "x-mark"),
    "check":          ("check",                "check",             "check"),
    "info":           ("info-circle",          "info",              "information-circle"),
    "triangle-alert": ("alert-triangle",       "warning",           "exclamation-triangle"),
    "file-text":      ("file-text",            "file-text",         "document-text"),
    "external-link":  ("external-link",        "arrow-square-out",  "arrow-top-right-on-square"),
    "square-pen":     ("edit",                 "pencil-simple",     "pencil-square"),
    "globe":          ("world",                "globe",             "globe-alt"),
    "wrench":         ("tool",                 "wrench",            "wrench"),
    "life-buoy":      ("lifebuoy",             "lifebuoy",          "lifebuoy"),
    "list":           ("list",                 "list",              "list-bullet"),
    "circle-help":    ("help-circle",          "question",          "question-mark-circle"),
}
SET_IDX = {"tabler": 0, "phosphor": 1, "heroicons": 2}


def parse_lucide():
    """Return [(selectors_list, stem), ...] from lucide.css."""
    css = open(os.path.join(ICONS, "lucide.css"), encoding="utf-8").read()
    out = []
    for block in css.split("}"):
        if "::before" not in block or "/svg/" not in block:
            continue
        head = block.split("{", 1)[0]
        sels = [s.strip() for s in head.split(",") if "::before" in s]
        m = re.search(r"/svg/([a-z0-9-]+)\.svg", block)
        if sels and m:
            out.append((sels, m.group(1)))
    return out


def fetch(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
        data = urllib.request.urlopen(req, timeout=20).read()
        if b"<svg" not in data[:512]:
            return False
        with open(dest, "wb") as fh:
            fh.write(data)
        return True
    except Exception:
        return False


def rule(sels, url):
    sel = ",\n".join(sels)
    return (f"{sel} {{\n"
            f"  content: \"\" !important;\n"
            f"  -webkit-mask: url('{url}') center / contain no-repeat;\n"
            f"  mask: url('{url}') center / contain no-repeat;\n"
            f"  background-color: currentColor;\n"
            f"  display: inline-block; width: 1em; height: 1em; vertical-align: -0.125em;\n"
            f"}}")


def main():
    blocks = parse_lucide()
    stems = sorted({stem for _, stem in blocks})
    for setname, tmpl in SETS.items():
        os.makedirs(os.path.join(ICONS, "svg", setname), exist_ok=True)
        resolved, fell_back = {}, []
        for stem in stems:
            cand = MAP.get(stem, (None, None, None))[SET_IDX[setname]]
            ok = False
            if cand:
                dest = os.path.join(ICONS, "svg", setname, f"{stem}.svg")
                ok = fetch(tmpl.format(cand), dest)
            if ok:
                resolved[stem] = f"{WEBURL}/svg/{setname}/{stem}.svg"
            else:
                resolved[stem] = f"{WEBURL}/svg/{stem}.svg"   # Lucide fallback
                fell_back.append(stem)
        rules = [rule(sels, resolved[stem]) for sels, stem in blocks]
        header = (f"/* Unraid Themer icon set: {setname.title()} — generated by "
                  f"scripts/gen_iconsets.py.\n   Missing icons fall back to Lucide. */\n")
        with open(os.path.join(ICONS, f"{setname}.css"), "w", encoding="utf-8") as fh:
            fh.write(header + "\n".join(rules) + "\n")
        print(f"{setname}: {len(stems)-len(fell_back)}/{len(stems)} native, "
              f"{len(fell_back)} fell back -> {', '.join(fell_back) if fell_back else 'none'}")


if __name__ == "__main__":
    main()
