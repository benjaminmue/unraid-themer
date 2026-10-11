#!/usr/bin/env python3
"""Run the plugin's URL check (include/fetch.php) against SSRF tricks.

Run:  python3 test/test_fetch_rules.py [--require-php] [--php "<command>"]

Every download the plugin makes runs on the server, inside the LAN. A URL
must only reach a public https host: never the server itself, the LAN,
Tailscale, link-local or metadata addresses, in any spelling. DNS answers come
from a fixed table here, so the check runs without network. CI passes
--require-php, so a runner without PHP fails instead of skipping."""
import json, os, shlex, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FETCH = os.path.join(ROOT, "plugin/usr/local/emhttp/plugins/unraid.themer/include/fetch.php")

# what the fake resolver answers
DNS = {
    "github.com":          ["140.82.121.4"],
    "cdn.example.com":     ["93.184.215.14", "2606:2800:21f:cb07:6820:80da:af6b:8b2c"],
    "xn--bcher-kva.ch":    ["185.199.108.153"],
    "localhost":           ["127.0.0.1", "::1"],
    "tower.lan":           ["192.168.170.15"],
    "rebind.example.com":  ["192.168.1.1"],
    "mixed.example.com":   ["93.184.215.14", "10.0.0.5"],
    "tailnet.example.com": ["100.101.102.103"],
    "mapped.example.com":  ["::ffff:7f00:1"],
    "nat64.example.com":   ["64:ff9b::a00:1"],
    "trailing.example.com": ["10.1.1.1"],
}

ALLOWED = [
    "https://github.com/benjaminmue/unraid-themer/raw/refs/heads/beta/themes/index.json",
    "https://cdn.example.com/logo.png?v=2",
    "https://xn--bcher-kva.ch/x.svg",
    "https://1.1.1.1/x.png",
    "https://[2606:4700:4700::1111]/x.png",
    "https://github.com:443/x.css",
]

REFUSED = [
    "http://github.com/x.png",                 # not https
    "ftp://github.com/x.png",
    "file:///etc/passwd",
    "gopher://127.0.0.1:6379/_x",
    "https://github.com:8443/x.png",           # other port
    "https://user:pw@github.com/x.png",        # userinfo
    "https://github.com\\@127.0.0.1/x.png",    # backslash parser confusion
    "https://127.0.0.1/x.png",
    "https://127.1/x.png",                     # short form of 127.0.0.1
    "https://2130706433/x.png",                # 127.0.0.1 as one number
    "https://0x7f.1/x.png",                    # hex form
    "https://017700000001/x.png",              # octal form
    "https://0.0.0.0/x.png",
    "https://[::1]/x.png",
    "https://[::ffff:127.0.0.1]/x.png",        # IPv4-mapped IPv6
    "https://[fe80::1]/x.png",                 # link-local
    "https://[fd00::1]/x.png",                 # unique local
    "https://10.0.0.1/x.png",
    "https://172.16.5.4/x.png",
    "https://192.168.170.15/x.png",            # the Unraid server
    "https://169.254.169.254/latest/meta-data/",
    "https://100.100.100.100/x.png",           # Tailscale / CGNAT
    "https://198.18.0.1/x.png",                # benchmark range
    "https://224.0.0.1/x.png",                 # multicast
    "https://localhost/x.png",
    "https://tower.lan/x.png",
    "https://rebind.example.com/x.png",        # public-looking name, private answer
    "https://mixed.example.com/x.png",         # one private answer is enough
    "https://tailnet.example.com/x.png",
    "https://mapped.example.com/x.png",
    "https://nat64.example.com/x.png",
    "https://trailing.example.com./x.png",     # trailing dot: not matched by curl's pin
    "https://github.com./x.png",               # even for a public host
    "https://unknown.example.com/x.png",       # does not resolve
    "https://exa mple.com/x.png",
]


def main():
    args = sys.argv[1:]
    php_cmd = args[args.index("--php") + 1] if "--php" in args else ("php" if shutil.which("php") else None)
    if not php_cmd:
        print("  FAIL  no php binary" if "--require-php" in args else "  NOTE  no php binary, nothing checked")
        sys.exit(1 if "--require-php" in args else 0)

    tmp = tempfile.mkdtemp(prefix="themer-fetch-")
    try:
        with open(os.path.join(tmp, "cases.json"), "w", encoding="utf-8") as f:
            json.dump({"dns": DNS, "urls": ALLOWED + REFUSED}, f)
        shutil.copy(FETCH, os.path.join(tmp, "fetch.php"))
        with open(os.path.join(tmp, "run.php"), "w", encoding="utf-8") as f:
            f.write("<?php\nrequire __DIR__ . '/fetch.php';\n"
                    "$c = json_decode(file_get_contents($argv[1]), true);\n"
                    "$dns = function ($h) use ($c) { return $c['dns'][$h] ?? []; };\n"
                    "$out = [];\n"
                    "foreach ($c['urls'] as $u) $out[$u] = themer_url_target($u, $dns)[2];\n"
                    "echo json_encode($out);\n")
        res = subprocess.run(shlex.split(php_cmd) + [os.path.join(tmp, "run.php"), os.path.join(tmp, "cases.json")],
                             capture_output=True, text=True, check=True)
        got = json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    bad = 0
    for url in ALLOWED + REFUSED:
        err = got[url]
        ok = (err == "") if url in ALLOWED else (err != "")
        if not ok or "--verbose" in args:
            print(f"  {'PASS' if ok else 'FAIL'}  {url}: " + (f"refused ({err})" if err else "allowed"))
        bad += 0 if ok else 1
    total = len(ALLOWED) + len(REFUSED)
    print(f"\n{total - bad}/{total} checks passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
