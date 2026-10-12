#!/usr/bin/env python3
"""Exercise the theme-refresh block from build.py's BOOT script in a sandbox.

Run:  python3 test/test_boot_refresh.py

The block is taken verbatim from build.py and only has its two absolute paths
rewritten, so what runs here is what runs on the server."""
import glob, hashlib, os, shutil, subprocess, sys, tempfile

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
    ("origin: no tmp left over",  not os.path.exists(f"{FLASH}/presets/.origin.tmp")
                                  and not os.path.exists(f"{FLASH}/presets/.bundled.tmp")),
]

# second run must change nothing (idempotent)
before = {f: sha(f"{FLASH}/presets/{f}") for f in os.listdir(f"{FLASH}/presets") if f.endswith(".css")}
subprocess.run(["bash", path], check=True, capture_output=True)
after = {f: sha(f"{FLASH}/presets/{f}") for f in os.listdir(f"{FLASH}/presets") if f.endswith(".css")}
checks.append(("second run idempotent", before == after and read(f"{FLASH}/presets/.origin") == origin))

# F: the registry fixed a bundled theme after this release and the user took it
#    with "Update installed" (the store records the registry hash + the sanitised
#    hash). A reboot with the same package must not put the older bundled copy back.
STORE = "/* v3 from the store */\n"
write(f"{FLASH}/presets/current.css", STORE)
rows_now = [l for l in read(f"{FLASH}/presets/.origin").split("\n") if l and not l.startswith("current|")]
store_hash = hashlib.sha256(STORE.encode()).hexdigest()
write(f"{FLASH}/presets/.origin", "\n".join(rows_now + [f"current|regsha|{store_hash}"]) + "\n")
subprocess.run(["bash", path], check=True, capture_output=True)
checks.append(("F store update survives reboot", read(f"{FLASH}/presets/current.css") == STORE))

# G: the next release ships the theme again (now at least as new as the store
#    copy); the untouched store copy is refreshed from the package.
V4 = "/* v4 shipped */\n"
write(f"{WEBROOT}/defaults/current.css", V4)
subprocess.run(["bash", path], check=True, capture_output=True)
checks.append(("G new package refreshes it", read(f"{FLASH}/presets/current.css") == V4))

# H: the refresh is interrupted (here: the copy fails). Nothing may be marked as
#    handled, so the next boot still delivers the new package version.
V5 = "/* v5 shipped */\n"
write(f"{WEBROOT}/defaults/current.css", V5)
shim = f"{root}/shim"
os.makedirs(shim)
write(f"{shim}/cp", "#!/bin/sh\nexit 1\n")
os.chmod(f"{shim}/cp", 0o755)
subprocess.run(["bash", path], check=True, capture_output=True,
               env={**os.environ, "PATH": f"{shim}:{os.environ['PATH']}"})
checks.append(("H failed copy leaves the theme", read(f"{FLASH}/presets/current.css") == V4))
subprocess.run(["bash", path], check=True, capture_output=True)
checks.append(("H next boot retries it",          read(f"{FLASH}/presets/current.css") == V5))

# I: stored images reach the webroot only through migrate-assets.php. Without
#    it (as here: the sandbox has no plugin files), no stored image may be
#    published at all, and stale webroot copies are gone.
for d in ("logo", "bg", "overrides"):
    os.makedirs(f"{FLASH}/{d}", exist_ok=True)
write(f"{FLASH}/logo/logo.svg", '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>')
write(f"{FLASH}/overrides/cpu.svg", '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
write(f"{FLASH}/bg/bg.png", "png bytes")
os.makedirs(f"{WEBROOT}/logo", exist_ok=True)
os.makedirs(f"{WEBROOT}/bg", exist_ok=True)
write(f"{WEBROOT}/logo/logo.svg", "stale copy from before the update")
write(f"{WEBROOT}/bg/bg.png", "stale copy from before the update")
subprocess.run(["bash", path], check=True, capture_output=True)
checks.append(("I no SVG served without the migration",
               not glob.glob(f"{WEBROOT}/**/*.svg", recursive=True)))
checks.append(("I no background or logo served without the migration",
               not glob.glob(f"{WEBROOT}/bg/*") and not glob.glob(f"{WEBROOT}/logo/*")))
checks.append(("I no stored theme served without the migration",
               not [p for p in glob.glob(f"{WEBROOT}/presets/*.css") if os.path.basename(p) != "bebamu.css"]))

bad = 0
for label, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    bad += 0 if ok else 1
shutil.rmtree(root)
print(f"\n{len(checks) - bad}/{len(checks)} Checks bestanden")
sys.exit(1 if bad else 0)
