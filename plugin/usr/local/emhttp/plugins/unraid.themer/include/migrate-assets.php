<?php
/* Boot-time pass over every image the user stored on flash (icon overrides,
 * logo, background): check it with the current rules and publish it to the
 * webroot. Earlier versions stored SVGs with a weaker check, or none for logo
 * and background, and took a picked server file by its name alone, so a fix
 * to the rules only protects anyone once those files are checked too.
 *
 * This is the only way a stored image reaches the webroot at boot; the boot
 * script copies none itself. If PHP or this script fails, nothing is
 * published, which costs a custom image until the next boot but never serves
 * an unchecked file. For each file:
 *   - an SVG that cleans: the cleaned bytes are published. The original on
 *     flash is never rewritten: cleaning can drop parts the allowlist does not
 *     know, and the user's file must survive that. It is cleaned again at
 *     every boot.
 *   - a raster image (logo, background): published as it is if its bytes are
 *     an image, and an SVG only under an .svg name
 *   - refused: it moves to quarantine/ on flash under a name that never
 *     replaces an earlier one, and is not published
 * Running it again changes nothing. Exit status 1 if anything failed.
 *
 * Usage (from the .plg boot script): php migrate-assets.php <flash dir> <webroot dir> */
if (PHP_SAPI !== 'cli') exit;   // never as a web request
require __DIR__ . '/svg.php';
require __DIR__ . '/asset.php';

$flash   = rtrim($argv[1] ?? '', '/');
$webroot = rtrim($argv[2] ?? '', '/');
if ($flash === '' || $webroot === '' || !is_dir($flash) || !is_dir($webroot)) exit(1);

function themer_write_atomic($path, $data) {
    $tmp = "$path.tmp";
    if (file_put_contents($tmp, $data) !== strlen($data)) { @unlink($tmp); return false; }
    if (!rename($tmp, $path)) { @unlink($tmp); return false; }
    return true;
}

// [bytes to publish, error] for one stored file
function themer_check_stored($raw, $name, $dir, $max) {
    $is_svg = strtolower(pathinfo($name, PATHINFO_EXTENSION)) === 'svg';
    if ($is_svg) return themer_sanitize_svg($raw, $max);
    // icon overrides are SVG only; anything else there is not ours to serve
    if ($dir === 'overrides') return ['', 'not an SVG'];
    $type = themer_image_type($raw);
    if ($type === '') return ['', 'not an image'];
    if ($type === 'svg') return ['', 'an SVG under a raster name'];
    return [$raw, ''];
}

$failed = false;
foreach (['overrides' => 65536, 'bg' => THEMER_IMAGE_MAX, 'logo' => THEMER_IMAGE_MAX] as $dir => $max) {
    $files = $dir === 'overrides' ? glob("$flash/$dir/*.svg") : glob("$flash/$dir/*");
    foreach ($files ?: [] as $file) {
        if (!is_file($file)) continue;
        $name = basename($file);
        $raw = file_get_contents($file);
        if ($raw === false) { $failed = true; echo "Unraid Themer: cannot read $dir/$name\n"; continue; }
        // an SVG logo or background keeps its own 1 MB limit
        [$clean, $err] = themer_check_stored($raw, $name, $dir, $dir === 'overrides' ? $max : 1024 * 1024);
        if ($err === '' && strlen($clean) > $max) $err = 'too large';
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
