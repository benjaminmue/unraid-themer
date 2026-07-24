#!/usr/bin/env python3
"""
gen_iconsets.py — generate alternative icon sets from the Lucide baseline.

For every icon slot in lucide.css we fetch each set's equivalent SVG; if a name
is missing we fall back to the bundled Lucide SVG, so a set is always complete
(never a broken icon). The three original sets (Tabler/Phosphor/Heroicons) are
fetched from their GitHub repos; the newer sets come from the Iconify API
(api.iconify.design/<prefix>/<name>.svg), which serves every set with a flat,
currentColor SVG — no per-repo folder layout to chase.

Outputs icons/<set>.css plus the fetched SVGs under icons/svg/<set>/.
Run from the repo root:  python3 scripts/gen_iconsets.py
"""
import os, re, urllib.request, urllib.parse

ICONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "plugin", "usr", "local", "emhttp", "plugins", "unraid.themer", "icons")
WEBURL = "/plugins/unraid.themer/icons"

# fetch strategy per set
GITHUB = {
    "tabler":    "https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{}.svg",
    "phosphor":  "https://raw.githubusercontent.com/phosphor-icons/core/main/assets/regular/{}.svg",
    "heroicons": "https://raw.githubusercontent.com/tailwindlabs/heroicons/master/optimized/24/outline/{}.svg",
}
ICONIFY = {  # set name -> iconify prefix
    "iconoir":   "iconoir",
    "remix":     "ri",
    "bootstrap": "bi",
    "carbon":    "carbon",
    "material":  "material-symbols",
}

# lucide stem -> name in the GitHub sets (tabler, phosphor, heroicons)
GH_NAMES = {
    "gauge":          ("gauge",              "gauge",             "chart-bar-square"),
    "circuit-board":  ("cpu-2",              "circuitry",         "cpu-chip"),
    "cpu":            ("cpu",                "cpu",               "cpu-chip"),
    "memory-stick":   ("device-sd-card",     "memory",            "server-stack"),
    "ethernet-port":  ("network",            "network",           "signal"),
    "battery-charging":("battery-charging",  "battery-charging",  "bolt"),
    "fan":            ("propeller",          "fan",               "arrow-path-rounded-square"),
    "container":      ("brand-docker",       "cube",              "cube"),
    "monitor":        ("device-desktop",     "desktop",           "computer-desktop"),
    "folder":         ("folder",             "folder",            "folder"),
    "users":          ("users",              "users",             "users"),
    "user":           ("user",               "user",              "user"),
    "hard-drive":     ("server-2",           "hard-drives",       "circle-stack"),
    "disc":           ("disc",               "disc",              "record"),
    "activity":       ("activity-heartbeat", "pulse",             "heart"),
    "server":         ("server",             "server",            "server"),
    "play":           ("player-play",        "play",              "play"),
    "square":         ("player-stop",        "stop",              "stop"),
    "pause":          ("player-pause",       "pause",             "pause"),
    "refresh-cw":     ("refresh",            "arrows-clockwise",  "arrow-path"),
    "rotate-cw":      ("rotate-clockwise",   "arrow-clockwise",   "arrow-path"),
    "power":          ("power",              "power",             "power"),
    "settings":       ("settings",           "gear",              "cog-6-tooth"),
    "trash-2":        ("trash",              "trash",             "trash"),
    "terminal":       ("terminal-2",         "terminal",          "command-line"),
    "download":       ("download",           "download-simple",   "arrow-down-tray"),
    "cloud-download": ("cloud-download",     "cloud-arrow-down",  "cloud-arrow-down"),
    "menu":           ("menu-2",             "list",              "bars-3"),
    "plus":           ("plus",               "plus",              "plus"),
    "chevron-up":     ("chevron-up",         "caret-up",          "chevron-up"),
    "chevron-down":   ("chevron-down",       "caret-down",        "chevron-down"),
    "search":         ("search",             "magnifying-glass",  "magnifying-glass"),
    "x":              ("x",                  "x",                 "x-mark"),
    "check":          ("check",              "check",             "check"),
    "info":           ("info-circle",        "info",              "information-circle"),
    "triangle-alert": ("alert-triangle",     "warning",           "exclamation-triangle"),
    "file-text":      ("file-text",          "file-text",         "document-text"),
    "external-link":  ("external-link",      "arrow-square-out",  "arrow-top-right-on-square"),
    "square-pen":     ("edit",               "pencil-simple",     "pencil-square"),
    "globe":          ("world",              "globe",             "globe-alt"),
    "wrench":         ("tool",               "wrench",            "wrench"),
    "life-buoy":      ("lifebuoy",           "lifebuoy",          "lifebuoy"),
    "list":           ("list",               "list",              "list-bullet"),
    "circle-help":    ("help-circle",        "question",          "question-mark-circle"),
    "log-out":        ("logout",             "sign-out",          "arrow-right-on-rectangle"),
    "copy":           ("copy",               "copy",              "document-duplicate"),
    "message-square": ("message",            "chat-text",         "chat-bubble-left-ellipsis"),
}
GH_IDX = {"tabler": 0, "phosphor": 1, "heroicons": 2}

# lucide stem -> candidate name(s) for the Iconify sets. First that resolves wins;
# otherwise the slot falls back to the bundled Lucide icon. A per-set default is
# applied for stems not listed here (identity, plus "-line" for remix).
ICONIFY_NAMES = {
    # stem:            iconoir,               remix (ri),          bootstrap (bi),      carbon,               material-symbols
    "gauge":          ("dashboard-speed",     "dashboard-3-line",  "speedometer2",      "meter",              "speed"),
    "circuit-board":  ("computer",            "cpu-line",          "cpu",               "chip",               "developer-board"),
    "cpu":            ("cpu",                 "cpu-line",          "cpu",               "chip",               "developer-board"),
    "memory-stick":   ("ram",                 "ram-2-line",        "memory",            "chip",               "memory"),
    "ethernet-port":  ("ethernet",            "base-station-line", "ethernet",          "network-3",          "lan"),
    "battery-charging":("battery-charging",   "battery-charge-line","battery-charging", "battery-charging",   "battery-charging-full"),
    "fan":            ("wind",                "windy-line",        "fan",               "fan",                "mode-fan"),
    "container":      ("box-iso",             "box-3-line",        "box",               "container-software", "deployed-code"),
    "monitor":        ("computer",            "computer-line",     "display",           "screen",             "desktop-windows"),
    "folder":         ("folder",              "folder-line",       "folder",            "folder",             "folder"),
    "users":          ("group",              "group-line",        "people",            "user-multiple",      "group"),
    "user":           ("user",                "user-line",         "person",            "user",               "person"),
    "hard-drive":     ("hdd",                 "hard-drive-2-line", "hdd-stack",         "data-base",          "hard-drive"),
    "disc":           ("db",                  "disc-line",         "disc",              "compact-disc",       "album"),
    "activity":       ("activity",            "pulse-line",        "activity",          "activity",           "vital-signs"),
    "server":         ("server",              "server-line",       "server",            "bare-metal-server",  "dns"),
    "play":           ("play",                "play-line",         "play",              "play",               "play-arrow"),
    "square":         ("square",              "stop-line",         "stop",              "stop",               "stop"),
    "pause":          ("pause",               "pause-line",        "pause",             "pause",              "pause"),
    "refresh-cw":     ("refresh-double",      "refresh-line",      "arrow-clockwise",   "renew",              "refresh"),
    "rotate-cw":      ("refresh",             "loop-right-line",   "arrow-clockwise",   "rotate-clockwise",   "rotate-right"),
    "power":          ("power-off",           "shut-down-line",    "power",             "power",              "power-settings-new"),
    "settings":       ("settings",            "settings-3-line",   "gear",              "settings",           "settings"),
    "trash-2":        ("trash",               "delete-bin-line",   "trash",             "trash-can",          "delete"),
    "terminal":       ("terminal",            "terminal-line",     "terminal",          "terminal",           "terminal"),
    "download":       ("download",            "download-line",     "download",          "download",           "download"),
    "cloud-download": ("cloud-download",      "cloud-line",        "cloud-download",    "cloud-download",     "cloud-download"),
    "menu":           ("menu",                "menu-line",         "list",              "menu",               "menu"),
    "plus":           ("plus",                "add-line",          "plus",              "add",                "add"),
    "chevron-up":     ("nav-arrow-up",        "arrow-up-s-line",   "chevron-up",        "chevron-up",         "keyboard-arrow-up"),
    "chevron-down":   ("nav-arrow-down",      "arrow-down-s-line", "chevron-down",      "chevron-down",       "keyboard-arrow-down"),
    "search":         ("search",              "search-line",       "search",            "search",             "search"),
    "x":              ("xmark",               "close-line",        "x",                 "close",              "close"),
    "check":          ("check",               "check-line",        "check",             "checkmark",          "check"),
    "info":           ("info-circle",         "information-line",  "info-circle",       "information",        "info"),
    "triangle-alert": ("warning-triangle",    "error-warning-line","exclamation-triangle","warning",          "warning"),
    "file-text":      ("page",                "file-text-line",    "file-text",         "document",           "description"),
    "external-link":  ("open-new-window",     "external-link-line","box-arrow-up-right","launch",             "open-in-new"),
    "square-pen":     ("edit-pencil",         "edit-line",         "pencil-square",     "edit",               "edit"),
    "globe":          ("globe",               "global-line",       "globe",             "wikis",              "language"),
    "wrench":         ("wrench",              "tools-line",        "wrench",            "tools",              "build"),
    "life-buoy":      ("lifebelt",            "lifebuoy-line",     "life-preserver",    "help",               "support"),
    "list":           ("list",                "list-check",        "list-ul",           "list",               "format-list-bulleted"),
    "circle-help":    ("help-circle",         "question-line",     "question-circle",   "help",               "help"),
    "log-out":        ("log-out",             "logout-box-line",   "box-arrow-right",   "logout",             "logout"),
    "copy":           ("copy",                "file-copy-line",    "copy",              "copy",               "content-copy"),
    "message-square": ("chat-bubble",         "chat-3-line",       "chat",              "chat",               "chat"),
}
ICONIFY_ORDER = ["iconoir", "remix", "bootstrap", "carbon", "material"]


def parse_lucide():
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
        data = urllib.request.urlopen(req, timeout=25).read()
        if b"<svg" not in data[:1024]:
            return False
        with open(dest, "wb") as fh:
            fh.write(data)
        return True
    except Exception:
        return False


def candidates(setname, stem):
    """Ordered candidate icon names to try for a set + stem."""
    if setname in GH_IDX:
        n = GH_NAMES.get(stem, (None, None, None))[GH_IDX[setname]]
        return [n] if n else []
    # iconify set
    idx = ICONIFY_ORDER.index(setname)
    listed = ICONIFY_NAMES.get(stem)
    cands = [listed[idx]] if listed and listed[idx] else []
    # per-set fallbacks by naming convention, then the plain stem
    if setname == "remix":
        cands += [stem + "-line", stem]
    elif setname == "material":
        cands += [stem, stem.replace("-", "_")]
    else:
        cands += [stem]
    # de-dup, keep order
    seen, out = set(), []
    for c in cands:
        if c and c not in seen:
            seen.add(c); out.append(c)
    return out


def url_for(setname, name):
    if setname in GITHUB:
        return GITHUB[setname].format(name)
    prefix = ICONIFY[setname]
    return f"https://api.iconify.design/{prefix}/{urllib.parse.quote(name)}.svg"


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
    all_sets = list(GITHUB.keys()) + list(ICONIFY.keys())
    for setname in all_sets:
        os.makedirs(os.path.join(ICONS, "svg", setname), exist_ok=True)
        resolved, fell_back = {}, []
        for stem in stems:
            ok = False
            for cand in candidates(setname, stem):
                dest = os.path.join(ICONS, "svg", setname, f"{stem}.svg")
                if fetch(url_for(setname, cand), dest):
                    ok = True
                    break
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
        print(f"{setname:10s}: {len(stems)-len(fell_back):2d}/{len(stems)} native, "
              f"{len(fell_back)} fell back -> {', '.join(fell_back) if fell_back else 'none'}")


if __name__ == "__main__":
    main()
