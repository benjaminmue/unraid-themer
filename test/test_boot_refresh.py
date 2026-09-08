#!/usr/bin/env python3
"""Exercise the theme-refresh block from build.py's BOOT script in a sandbox.

Run:  python3 test/test_boot_refresh.py

The block is taken verbatim from build.py and only has its two absolute paths
rewritten, so what runs here is what runs on the server."""
import hashlib, os, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build  # noqa: E402  (module constants only; main() is __main__-gated)

root = tempfile.mkdtemp(prefix="themer-boot-")
FLASH, WEBROOT = f"{root}/flash", f"{root}/webroot"
for d in (f"{FLASH}/presets", f"{WEBROOT}/defaults", f"{WEBROOT}/presets"):
    os.makedirs(d)

script = (build.BOOT
          .replace("/boot/config/plugins/unraid.themer", FLASH)
          .replace("/usr/local/emhttp/plugins/unraid.themer", WEBROOT))
path = f"{root}/boot.sh"
open(path, "w").write(script)

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def write(p, text):
    open(p, "w").write(text)

NEW, OLD, EDIT = "/* v2 shipped */\n", "/* v1 shipped */\n", "/* v1 shipped */\n/* my tweak */\n"

open(f"{FLASH}/presets/.seeded", "w").close()   # an existing install, not a fresh one

# package ships v2 of four themes
for stem in ("current", "stale_norecord", "stale_recorded", "edited", "removed"):
    write(f"{WEBROOT}/defaults/{stem}.css", NEW)

# A: installed, old, no .origin record at all (an install predating this)
write(f"{FLASH}/presets/stale_norecord.css", OLD)
# B: installed, old, recorded as untouched since we wrote it
write(f"{FLASH}/presets/stale_recorded.css", OLD)
# C: installed, old, but the user edited it
write(f"{FLASH}/presets/edited.css", EDIT)
# D: installed and already current
write(f"{FLASH}/presets/current.css", NEW)
# E: uninstalled by the user -> no file at all
old_hash = hashlib.sha256(OLD.encode()).hexdigest()
write(f"{FLASH}/presets/.origin",
      f"stale_recorded|deadbeef|{old_hash}\n"
      f"edited|deadbeef|{old_hash}\n"          # recorded hash != the edited file
      f"keepme|cafe|f00d\n")                    # unrelated entry must survive

subprocess.run(["bash", path], check=True, capture_output=True)

def read(p):
    return open(p).read()

checks = [
    ("A no record   -> refreshed", read(f"{FLASH}/presets/stale_norecord.css") == NEW),
    ("B untouched   -> refreshed", read(f"{FLASH}/presets/stale_recorded.css") == NEW),
    ("C edited      -> kept",      read(f"{FLASH}/presets/edited.css") == EDIT),
    ("D current     -> unchanged", read(f"{FLASH}/presets/current.css") == NEW),
    ("E uninstalled -> stays gone", not os.path.exists(f"{FLASH}/presets/removed.css")),
]
origin = read(f"{FLASH}/presets/.origin")
rows = [l.split("|") for l in origin.strip().split("\n") if l]
by_stem = {r[0]: r for r in rows}
new_hash = hashlib.sha256(NEW.encode()).hexdigest()
checks += [
    ("origin: one row per theme", len(rows) == len({r[0] for r in rows})),
    ("origin: A recorded",        by_stem.get("stale_norecord", [None]*3)[2] == new_hash),
    ("origin: B updated",         by_stem.get("stale_recorded", [None]*3)[2] == new_hash),
    ("origin: C untouched",       by_stem.get("edited", [None]*3)[2] == old_hash),
    ("origin: unrelated kept",    "keepme" in by_stem),
    ("origin: D recorded though unchanged", by_stem.get("current", [None]*3)[2] == new_hash),
    ("origin: no tmp left over",  not os.path.exists(f"{FLASH}/presets/.origin.tmp")),
]

# second run must change nothing (idempotent)
before = {f: sha(f"{FLASH}/presets/{f}") for f in os.listdir(f"{FLASH}/presets") if f.endswith(".css")}
subprocess.run(["bash", path], check=True, capture_output=True)
after = {f: sha(f"{FLASH}/presets/{f}") for f in os.listdir(f"{FLASH}/presets") if f.endswith(".css")}
checks.append(("second run idempotent", before == after and read(f"{FLASH}/presets/.origin") == origin))

bad = 0
for label, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    bad += 0 if ok else 1
shutil.rmtree(root)
print(f"\n{len(checks) - bad}/{len(checks)} Checks bestanden")
sys.exit(1 if bad else 0)
