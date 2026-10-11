#!/usr/bin/env python3
"""Run the plugin's image reader (include/asset.php) against planted links.

Run:  python3 test/test_asset_rules.py [--require-php] [--php "<command>"]

A background or logo picked as a file on the server is copied into the
webroot. Only a real image below the allowed root may get there: no symlink,
no path that leaves the root, no file that merely has an image name. The
allowed root is /mnt/ in the plugin; here it is a temporary directory. CI
passes --require-php, so a runner without PHP fails instead of skipping."""
import json, os, shlex, shutil, struct, subprocess, sys, tempfile, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = os.path.join(ROOT, "plugin/usr/local/emhttp/plugins/unraid.themer/include/asset.php")


def png():
    """A real 1x1 PNG."""
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b""))


SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect width="1" height="1"/></svg>'


def build(tmp):
    """Fixture tree: share/ is the allowed root, outside/ holds a secret."""
    share, outside = os.path.join(tmp, "share"), os.path.join(tmp, "outside")
    os.makedirs(os.path.join(share, "pics"))
    os.makedirs(outside)
    w = lambda p, b: open(p, "wb").write(b)
    w(os.path.join(share, "pics/logo.png"), png())
    w(os.path.join(share, "pics/logo.svg"), SVG)
    w(os.path.join(share, "pics/fake.png"), b"root:$6$secret:19000:0:99999:7:::\n")
    w(os.path.join(outside, "shadow.png"), png())   # an image, but outside the root
    w(os.path.join(outside, "shadow"), b"root:$6$secret\n")
    os.symlink(os.path.join(outside, "shadow"), os.path.join(share, "pics/link.png"))
    os.symlink(os.path.join(share, "pics/logo.png"), os.path.join(share, "pics/inside-link.png"))
    os.symlink(outside, os.path.join(share, "dirlink"))
    os.symlink(os.path.join(share, "pics"), os.path.join(share, "pics-alias"))
    os.makedirs(share + "x")                         # shares a prefix with the root
    w(os.path.join(share + "x", "logo.png"), png())
    return share


# path (relative to the fixture dir) -> expected type, or None for refused
CASES = {
    "share/pics/logo.png":         "png",
    "share/pics/logo.svg":         "svg",
    "share/pics-alias/logo.png":   "png",    # linked directory that stays inside the root
    "share/pics/fake.png":         None,     # image name, not image bytes
    "share/pics/link.png":         None,     # symlink to a system file
    "share/pics/inside-link.png":  None,     # every symlinked file is refused
    "share/dirlink/shadow.png":    None,     # linked directory leading out of the root
    "share/../outside/shadow.png": None,     # dot-dot out of the root
    "sharex/logo.png":             None,     # prefix of the root, not below it
    "share/pics/missing.png":      None,
}


def main():
    args = sys.argv[1:]
    php_cmd = args[args.index("--php") + 1] if "--php" in args else ("php" if shutil.which("php") else None)
    if not php_cmd:
        print("  FAIL  no php binary" if "--require-php" in args else "  NOTE  no php binary, nothing checked")
        sys.exit(1 if "--require-php" in args else 0)

    tmp = tempfile.mkdtemp(prefix="themer-asset-")
    try:
        share = build(tmp)
        paths = {rel: os.path.join(tmp, rel) for rel in CASES}
        with open(os.path.join(tmp, "cases.json"), "w", encoding="utf-8") as f:
            json.dump({"root": share + "/", "paths": paths}, f)
        shutil.copy(ASSET, os.path.join(tmp, "asset.php"))
        with open(os.path.join(tmp, "run.php"), "w", encoding="utf-8") as f:
            f.write("<?php\nrequire __DIR__ . '/asset.php';\n"
                    "$c = json_decode(file_get_contents($argv[1]), true);\n"
                    "$out = [];\n"
                    "foreach ($c['paths'] as $k => $p) { [$d, $ext, $err] = themer_read_server_image($p, $c['root']);"
                    " $out[$k] = [$ext, $err]; }\n"
                    "echo json_encode($out);\n")
        res = subprocess.run(shlex.split(php_cmd) + [os.path.join(tmp, "run.php"), os.path.join(tmp, "cases.json")],
                             capture_output=True, text=True, check=True)
        got = json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    bad = 0
    for rel, want in CASES.items():
        ext, err = got[rel]
        ok = (ext == want and not err) if want else (ext == "" and err != "")
        if not ok or "--verbose" in args:
            print(f"  {'PASS' if ok else 'FAIL'}  {rel}: " + (f"read as {ext}" if ext else f"refused ({err})"))
        bad += 0 if ok else 1
    print(f"\n{len(CASES) - bad}/{len(CASES)} checks passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
