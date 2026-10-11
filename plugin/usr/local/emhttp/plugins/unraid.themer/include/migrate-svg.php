<?php
/* Boot-time pass over every SVG the user stored on flash (icon overrides, logo,
 * background): clean it with the current sanitiser and publish the cleaned
 * bytes to the webroot. Earlier versions stored SVGs with a weaker check, or
 * none for logo and background, so a fix to the sanitiser only protects anyone
 * once those files are cleaned too.
 *
 * This is the only way an SVG reaches the webroot at boot; the boot script
 * copies none itself. If PHP or this script fails, nothing is published,
 * which costs a custom icon until the next boot but never serves an unchecked
 * document. For each file:
 *   - cleans: the cleaned bytes are published. The original on flash is never
 *     rewritten: cleaning can drop parts the allowlist does not know, and the
 *     user's file must survive that. It is cleaned again at every boot.
 *   - refused: it moves to quarantine/ on flash under a name that never
 *     replaces an earlier one, and is not published
 * Running it again changes nothing. Exit status 1 if anything failed.
 *
 * Usage (from the .plg boot script): php migrate-svg.php <flash dir> <webroot dir> */
if (PHP_SAPI !== 'cli') exit;   // never as a web request
require __DIR__ . '/svg.php';

$flash   = rtrim($argv[1] ?? '', '/');
$webroot = rtrim($argv[2] ?? '', '/');
if ($flash === '' || $webroot === '' || !is_dir($flash) || !is_dir($webroot)) exit(1);

function themer_write_atomic($path, $data) {
    $tmp = "$path.tmp";
    if (file_put_contents($tmp, $data) !== strlen($data)) { @unlink($tmp); return false; }
    if (!rename($tmp, $path)) { @unlink($tmp); return false; }
    return true;
}

$failed = false;
foreach (['overrides' => 65536, 'bg' => 1024 * 1024, 'logo' => 1024 * 1024] as $dir => $max) {
    foreach (glob("$flash/$dir/*.svg") ?: [] as $file) {
        $name = basename($file);
        $raw = file_get_contents($file);
        if ($raw === false) { $failed = true; echo "Unraid Themer: cannot read $dir/$name\n"; continue; }
        [$clean, $err] = themer_sanitize_svg($raw, $max);
        if ($err !== '') {
            @mkdir("$flash/quarantine", 0700, true);
            $dest = "$flash/quarantine/$dir-$name";
            for ($i = 1; file_exists($dest); $i++) $dest = "$flash/quarantine/$dir-$i-$name";
            if (rename($file, $dest)) {
                echo "Unraid Themer: quarantined $dir/$name as " . basename($dest) . " ($err)\n";
            } else {
                $failed = true;   // stays on flash, but is not published
                echo "Unraid Themer: could not quarantine $dir/$name ($err), not served\n";
            }
            continue;
        }
        @mkdir("$webroot/$dir", 0755, true);
        if (!themer_write_atomic("$webroot/$dir/$name", $clean)) {
            $failed = true;
            echo "Unraid Themer: could not publish $dir/$name\n";
        }
    }
}
exit($failed ? 1 : 0);
