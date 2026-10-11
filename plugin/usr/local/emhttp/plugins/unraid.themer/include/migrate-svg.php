<?php
/* Boot-time pass over every SVG the user stored on flash (icon overrides, logo,
 * background) through the current sanitiser, before the boot script copies
 * them into the webroot. Earlier versions stored SVGs with a weaker check, or
 * none for logo and background, so a security fix to the sanitiser only
 * protects anyone once those files are cleaned too.
 *
 * A file that cleans is rewritten in place; one that is refused moves to
 * quarantine/ on flash, out of anything the webGui serves, so nothing is lost.
 * Running it again changes nothing.
 *
 * Usage (from the .plg boot script): php migrate-svg.php <flash dir> */
if (PHP_SAPI !== 'cli') exit;   // never as a web request
require __DIR__ . '/svg.php';

$flash = rtrim($argv[1] ?? '', '/');
if ($flash === '' || !is_dir($flash)) exit(1);

foreach (['overrides' => 65536, 'bg' => 1024 * 1024, 'logo' => 1024 * 1024] as $dir => $max) {
    foreach (glob("$flash/$dir/*.svg") ?: [] as $file) {
        $raw = (string) file_get_contents($file);
        [$clean, $err] = themer_sanitize_svg($raw, $max);
        if ($err !== '') {
            @mkdir("$flash/quarantine", 0700, true);
            rename($file, "$flash/quarantine/$dir-" . basename($file));
            echo "Unraid Themer: quarantined $dir/" . basename($file) . " ($err)\n";
        } elseif ($clean !== $raw) {
            file_put_contents($file, $clean);
            echo "Unraid Themer: cleaned $dir/" . basename($file) . "\n";
        }
    }
}
