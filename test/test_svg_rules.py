#!/usr/bin/env python3
"""Run the plugin's SVG sanitiser (include/svg.php) against attacks and real icons.

Run:  python3 test/test_svg_rules.py [--require-php] [--php "<command>"]

Every attack must come out either refused or stripped of anything that could
run script or load something. Every bundled icon must come out with all of its
drawing intact. CI passes --require-php, so a runner without PHP fails instead
of skipping."""
import glob, json, os, re, shlex, shutil, subprocess, sys, tempfile

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

# what must never survive in a cleaned document
DANGER = re.compile(r"script|\son\w+\s*=|href|javascript|foreignObject|<\w*:?animate|<\w*:?set\b|<\w*:?use\b"
                    r"|<\w*:?image\b|style|<!|<\?|xml:base|https?:(?!//www\.w3\.org/)", re.I)

# must be accepted with every drawing element kept, besides the bundled icons
HARMLESS = {
    "inline icon without xmlns": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 4h16v16H4z"/><circle cx="12" cy="12" r="3"/></svg>',
    "gradient by reference":     f'<svg {SVG} viewBox="0 0 10 10"><defs><linearGradient id="g"><stop offset="0" stop-color="#e32929"/></linearGradient></defs><rect width="10" height="10" fill="url(#g)"/></svg>',
}

DRAWING = re.compile(r"<(?:\w+:)?(path|circle|ellipse|line|polyline|polygon|rect|g)\b")


def run_php(cases, php_cmd):
    tmp = tempfile.mkdtemp(prefix="themer-svg-")
    try:
        with open(os.path.join(tmp, "cases.json"), "w", encoding="utf-8") as f:
            json.dump(cases, f)
        shutil.copy(os.path.join(PLUGIN, "include", "svg.php"), os.path.join(tmp, "svg.php"))
        with open(os.path.join(tmp, "run.php"), "w", encoding="utf-8") as f:
            f.write("<?php\nrequire __DIR__ . '/svg.php';\n"
                    "$cases = json_decode(file_get_contents($argv[1]), true);\n"
                    "$out = [];\n"
                    "foreach ($cases as $k => $svg) $out[$k] = themer_sanitize_svg($svg);\n"
                    "echo json_encode($out);\n")
        cmd = shlex.split(php_cmd) + [os.path.join(tmp, "run.php"), os.path.join(tmp, "cases.json")]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
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
    res = run_php({**ATTACKS, **keep}, php_cmd)

    checks = []
    for name in ATTACKS:
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

    bad = 0
    for label, ok, detail in checks:
        if not ok or "--verbose" in args:
            print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))
        bad += 0 if ok else 1
    print(f"\n{len(checks) - bad}/{len(checks)} checks passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
