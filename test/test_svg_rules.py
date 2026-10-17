#!/usr/bin/env python3
"""Run the plugin's SVG sanitiser (include/svg.php) against attacks and real icons.

Run:  python3 test/test_svg_rules.py [--require-php] [--php "<command>"]

Every attack must come out either refused or stripped of anything that could
run script or load something. Every bundled icon must come out with all of its
drawing intact. CI passes --require-php, so a runner without PHP fails instead
of skipping."""
import base64, glob, json, os, re, shlex, shutil, struct, subprocess, sys, tempfile, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugin/usr/local/emhttp/plugins/unraid.themer")
SVG = 'xmlns="http://www.w3.org/2000/svg"'

ATTACKS = {
    "script":                f'<svg {SVG}><script>alert(1)</script><path d="M0 0h1"/></svg>',
    "svg-prefixed script":   f'<s:svg xmlns:s="http://www.w3.org/2000/svg"><s:script>alert(1)</s:script></s:svg>',
    "inner prefixed script": f'<svg {SVG} xmlns:s="http://www.w3.org/2000/svg"><s:script>alert(1)</s:script></svg>',
    "xhtml script":          f'<svg {SVG} xmlns:h="http://www.w3.org/1999/xhtml"><h:script>alert(1)</h:script></svg>',
    "onload":                f'<svg {SVG} onload="alert(1)"><path d="M0 0"/></svg>',
    "onload on child":       f'<svg {SVG}><path onclick="alert(1)" d="M0 0"/></svg>',
    "entity-encoded href":   f'<svg {SVG}><a href="jav&#x61;script:alert(1)"><path d="M0 0"/></a></svg>',
    "xlink href":            f'<svg {SVG} xmlns:xlink="http://www.w3.org/1999/xlink"><a xlink:href="&#x68;ttps://evil.example"><rect width="1" height="1"/></a></svg>',
    "animate to javascript": f'<svg {SVG} xmlns:s="http://www.w3.org/2000/svg"><a><s:animate attributeName="href" to="jav&#x61;script:alert(1)"/></a></svg>',
    "set element":           f'<svg {SVG}><set attributeName="onmouseover" to="alert(1)"/></svg>',
    "foreignObject":         f'<svg {SVG}><foreignObject><body xmlns="http://www.w3.org/1999/xhtml"><script>alert(1)</script></body></foreignObject></svg>',
    "use external":          f'<svg {SVG}><use href="https://evil.example/x.svg#a"/></svg>',
    "image external":        f'<svg {SVG}><image href="https://evil.example/x.png" width="1" height="1"/></svg>',
    "style element":         f'<svg {SVG}><style>@import url(https://evil.example/x.css);</style></svg>',
    "style attribute":       f'<svg {SVG}><rect style="fill:url(https://evil.example/x)" width="1" height="1"/></svg>',
    "fill url external":     f'<svg {SVG}><rect fill="url(https://evil.example/x#a)" width="1" height="1"/></svg>',
    "cdata script":          f'<svg {SVG}><script><![CDATA[alert(1)]]></script></svg>',
    "doctype entity":        f'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg {SVG}><title>&x;</title></svg>',
    "processing instruction": f'<?xml-stylesheet href="https://evil.example/x.css"?><svg {SVG}><path d="M0 0"/></svg>',
    "html not svg":          '<html><body><script>alert(1)</script></body></html>',
    "svg without namespace": '<svg><script>alert(1)</script></svg>',
    "xml:base":              f'<svg {SVG} xml:base="https://evil.example/"><path d="M0 0"/></svg>',
}

# attacks that only exist as bytes
BYTE_ATTACKS = {
    "UTF-16 with DOCTYPE":   ('<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
                              f'<svg {SVG}><title>&x;</title></svg>').encode("utf-16"),
}

# what must never survive in a cleaned document
DANGER = re.compile(r"script|\son\w+\s*=|href|javascript|foreignObject|<\w*:?animate|<\w*:?set\b|<\w*:?use\b"
                    r"|<\w*:?image\b|style|<!|<\?|xml:base|https?:(?!//www\.w3\.org/)", re.I)

# must be accepted with every drawing element kept, besides the bundled icons
HARMLESS = {
    "inline icon without xmlns": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 4h16v16H4z"/><circle cx="12" cy="12" r="3"/></svg>',
    "outline icon via style":    f'<svg {SVG} viewBox="0 0 24 24"><path style="fill:none;stroke:currentColor;stroke-width:2" d="M2 2H22V22H2Z"/></svg>',
    "text logo":                 f'<svg {SVG} viewBox="0 0 200 40"><text x="0" y="30" font-family="Inter, sans-serif" font-size="28" font-weight="900" fill="#f0f0f0">Brand<tspan fill="#e63312">.</tspan></text></svg>',
    "gradient by reference":     f'<svg {SVG} viewBox="0 0 10 10"><defs><linearGradient id="g"><stop offset="0" stop-color="#e32929"/></linearGradient></defs><rect width="10" height="10" fill="url(#g)"/></svg>',
}

def _png():
    """A real 1x1 PNG."""
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b""))


PNG = _png()

DRAWING = re.compile(r"<(?:\w+:)?(path|circle|ellipse|line|polyline|polygon|rect|g|text|tspan)\b")


def run_php(cases, php_cmd):
    tmp = tempfile.mkdtemp(prefix="themer-svg-")
    try:
        with open(os.path.join(tmp, "cases.json"), "w", encoding="utf-8") as f:
            # base64, so byte cases (UTF-16) reach PHP unchanged
            json.dump({k: base64.b64encode(v if isinstance(v, bytes) else v.encode("utf-8")).decode()
                       for k, v in cases.items()}, f)
        shutil.copy(os.path.join(PLUGIN, "include", "svg.php"), os.path.join(tmp, "svg.php"))
        with open(os.path.join(tmp, "run.php"), "w", encoding="utf-8") as f:
            f.write("<?php\nrequire __DIR__ . '/svg.php';\n"
                    "$cases = json_decode(file_get_contents($argv[1]), true);\n"
                    "$out = [];\n"
                    "foreach ($cases as $k => $svg) $out[$k] = themer_sanitize_svg(base64_decode($svg));\n"
                    "echo json_encode($out);\n")
        cmd = shlex.split(php_cmd) + [os.path.join(tmp, "run.php"), os.path.join(tmp, "cases.json")]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def migration_checks(php_cmd):
    """Boot migration (include/migrate-assets.php) on a fake flash directory."""
    tmp = tempfile.mkdtemp(prefix="themer-svgmig-")
    try:
        flash, web = os.path.join(tmp, "flash"), os.path.join(tmp, "web")
        for d in ("overrides", "bg", "logo", "presets"):
            os.makedirs(os.path.join(flash, d))
        os.makedirs(web)
        files = {
            "overrides/cpu.svg": ATTACKS["inner prefixed script"],     # cleanable
            "overrides/ok.svg":  open(sorted(glob.glob(os.path.join(PLUGIN, "icons/svg/*.svg")))[0]).read(),
            "logo/logo.svg":     ATTACKS["onload"],                    # cleanable
            "bg/bg.svg":         ATTACKS["doctype entity"],            # refused
            "bg/bg.png":         PNG,                                  # a real image
            "logo/logo.jpg":     "root:$6$secret\n",                   # image name, not image bytes
            "logo/logo.gif":     ATTACKS["script"],                    # an SVG under a raster name
            "logo/logo.php":     PNG + b"<?php system($_GET[1]); ?>",  # an image, but a name the webroot runs
            "bg/bg.html":        b"GIF89a<script>alert(1)</script>",   # an image, but a name the webroot renders
            "presets/good.css":  ":root{--background-color:#101010}",  # passes the CSS rules
            "presets/old.css":   ':root{--x:1} body{background:image-set("https://evil.example/x" 1x)}',
        }
        for rel, body in files.items():
            with open(os.path.join(flash, rel), "wb") as f:
                f.write(body if isinstance(body, bytes) else body.encode("utf-8"))
        plug = os.path.join(tmp, "plugin", "include")
        os.makedirs(plug)
        for f in ("svg.php", "asset.php", "css.php", "migrate-assets.php"):
            shutil.copy(os.path.join(PLUGIN, "include", f), plug)
        run = lambda: subprocess.run(shlex.split(php_cmd) + [os.path.join(plug, "migrate-assets.php"), flash, web],
                                     capture_output=True, text=True, check=True)
        run()
        webfile = lambda rel: os.path.join(web, rel)
        published = {rel: open(webfile(rel), encoding="utf-8").read()
                     for rel in ("overrides/cpu.svg", "overrides/ok.svg", "logo/logo.svg") if os.path.exists(webfile(rel))}
        read = lambda rel: open(os.path.join(flash, rel), encoding="utf-8").read()
        first = {rel: read(rel) for rel in ("overrides/cpu.svg", "overrides/ok.svg", "logo/logo.svg")}
        run()
        second = {rel: read(rel) for rel in first}
        again = {rel: open(webfile(rel), encoding="utf-8").read() for rel in published}
        # a second refused file of the same name must not replace the first one
        with open(os.path.join(flash, "bg/bg.svg"), "w", encoding="utf-8") as f:
            f.write(ATTACKS["html not svg"])
        run()
        quarantined = sorted(os.listdir(os.path.join(flash, "quarantine")))
        photo = open(webfile("bg/bg.png"), "rb").read() if os.path.exists(webfile("bg/bg.png")) else b""
        blocked = open(webfile("blocked-themes"), encoding="utf-8").read() if os.path.exists(webfile("blocked-themes")) else ""
        return [
            ("migration: originals on flash are never rewritten",
             all(first[rel] == files[rel] for rel in first), ""),
            ("migration: published copies are clean",
             all(not DANGER.search(v) for v in published.values()) and len(published) == 3, ""),
            ("migration: harmless icon published with its drawing",
             len(DRAWING.findall(published.get("overrides/ok.svg", ""))) == len(DRAWING.findall(files["overrides/ok.svg"])), ""),
            ("migration: refused file is not published", not os.path.exists(webfile("bg/bg.svg")), ""),
            ("migration: quarantine never overwrites",
             sorted(q for q in quarantined if q.startswith("bg-") and q.endswith(".svg")) == ["bg-1-bg.svg", "bg-bg.svg"], " ".join(quarantined)),
            ("migration: refused background quarantined",
             not os.path.exists(os.path.join(flash, "bg/bg.svg"))
             and os.path.exists(os.path.join(flash, "quarantine/bg-bg.svg")), ""),
            ("migration: real raster image published unchanged",
             photo == PNG and open(os.path.join(flash, "bg/bg.png"), "rb").read() == PNG, ""),
            ("migration: fake raster image quarantined, not published",
             "logo-logo.jpg" in quarantined and not os.path.exists(webfile("logo/logo.jpg")), " ".join(quarantined)),
            ("migration: SVG under a raster name quarantined, not published",
             "logo-logo.gif" in quarantined and not os.path.exists(webfile("logo/logo.gif")), " ".join(quarantined)),
            ("migration: image under a .php or .html name quarantined, not published",
             {"logo-logo.php", "bg-bg.html"} <= set(quarantined)
             and not os.path.exists(webfile("logo/logo.php")) and not os.path.exists(webfile("bg/bg.html")), " ".join(quarantined)),
            ("migration: theme within the rules published",
             os.path.exists(webfile("presets/good.css")), ""),
            ("migration: theme breaking a rule not published, kept on flash, listed",
             not os.path.exists(webfile("presets/old.css")) and read("presets/old.css") == files["presets/old.css"]
             and blocked.startswith("old\tloads a resource"), blocked.strip()),
            ("migration: second run changes nothing", first == second and again == published, ""),
        ]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = sys.argv[1:]
    php_cmd = args[args.index("--php") + 1] if "--php" in args else ("php" if shutil.which("php") else None)
    if not php_cmd:
        print("  FAIL  no php binary" if "--require-php" in args else "  NOTE  no php binary, nothing checked")
        sys.exit(1 if "--require-php" in args else 0)

    icons = {"icon " + os.path.relpath(p, PLUGIN): open(p, encoding="utf-8").read()
             for p in sorted(glob.glob(os.path.join(PLUGIN, "icons/svg/**/*.svg"), recursive=True))}
    keep = {**HARMLESS, **icons}
    attacks = {**ATTACKS, **BYTE_ATTACKS}
    res = run_php({**attacks, **keep}, php_cmd)

    checks = []
    for name in attacks:
        clean, err = res[name]
        hit = DANGER.search(clean or "")
        checks.append((f"attack {name}: " + (f"refused ({err})" if err else "cleaned"),
                       bool(err) or not hit, hit.group(0) if hit else ""))
    lost = []
    for name, src in keep.items():
        clean, err = res[name]
        if err or len(DRAWING.findall(clean)) != len(DRAWING.findall(src)):
            lost.append(f"{name}: {err or 'drawing elements lost'}")
    checks.append((f"{len(HARMLESS)} harmless SVGs and {len(icons)} bundled icons keep all drawing elements",
                   not lost, "; ".join(lost[:5])))
    grad = res["gradient by reference"][0]
    checks.append(("url(#id) reference survives", 'fill="url(#g)"' in grad, grad[:120]))
    styled = res["outline icon via style"][0]
    checks.append(("style declarations become attributes",
                   all(a in styled for a in ('fill="none"', 'stroke="currentColor"', 'stroke-width="2"'))
                   and "style" not in styled, styled[:160]))
    logo = res["text logo"][0]
    checks.append(("text content and font attributes survive",
                   "Brand" in logo and 'font-weight="900"' in logo and 'font-family="Inter, sans-serif"' in logo, logo[:160]))
    checks += migration_checks(php_cmd)

    bad = 0
    for label, ok, detail in checks:
        if not ok or "--verbose" in args:
            print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))
        bad += 0 if ok else 1
    print(f"\n{len(checks) - bad}/{len(checks)} checks passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
