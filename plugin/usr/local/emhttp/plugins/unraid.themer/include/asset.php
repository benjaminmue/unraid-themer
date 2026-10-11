<?php
/* Reading a background or logo image the user picked, by URL or as a file on
 * this server. Whatever is read here is copied into the webroot and served by
 * the webGui, so it must really be an image and must come from a place the
 * user meant.
 *
 * A file path is only accepted below /mnt/ (the array, pools and unassigned
 * disks) after every symlink in it is resolved. A share is writable over SMB,
 * NFS and from containers, so a link planted there (`logo.png ->
 * /boot/config/shadow`) would otherwise copy a system file into the webroot.
 * The type comes from the bytes, never from the file name.
 *
 * test/test_asset_rules.py runs these functions against planted links. */

const THEMER_IMAGE_MAX = 15 * 1024 * 1024;

// The image type of $data as a file extension, '' when it is not an image.
// finfo reports an SVG without an XML prolog as text, so an SVG is also
// recognised by its root element; the SVG sanitiser checks the rest.
function themer_image_type($data) {
    $map = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp',
            'image/gif' => 'gif', 'image/svg+xml' => 'svg', 'image/avif' => 'avif',
            'image/x-ms-bmp' => 'bmp', 'image/bmp' => 'bmp'];
    $fi = finfo_open(FILEINFO_MIME_TYPE);
    $mime = finfo_buffer($fi, $data);
    finfo_close($fi);
    if (isset($map[$mime])) return $map[$mime];
    if (in_array($mime, ['text/xml', 'application/xml', 'text/plain', 'text/html'], true)
        && preg_match('/^\s*(<\?xml[^>]*>\s*)?(<!--.*?-->\s*)*<svg[\s>]/is', $data)) return 'svg';
    return '';
}

// Read an image file on this server: [data, ext, error]. $root only differs in tests.
// A writer in the share could swap the file or a directory above it for a
// symlink between the checks and the open. So the checks run again after the
// open: the path must still resolve to itself below $root, and the file there
// must be the one that was opened (same device and inode). /mnt holds other
// file systems than / and /boot, so no hard link can make a system file pass.
function themer_read_server_image($path, $root = '/mnt/') {
    if (is_link($path)) return ['', '', 'symlinks are not accepted, pick the file itself'];
    $real = realpath($path);
    if ($real === false || !is_file($real)) return ['', '', 'file not found on the server'];
    // every link in the path is resolved by now, so this is where the bytes live
    if (strpos($real, $root) !== 0) return ['', '', 'only files under /mnt/ can be used'];
    if (filesize($real) > THEMER_IMAGE_MAX) return ['', '', 'image too large (>15 MB)'];
    $fh = @fopen($real, 'rb');
    if ($fh === false) return ['', '', 'could not read that file'];
    $st = fstat($fh);
    $now = @stat($real);
    $same = $st && $now && realpath($real) === $real
        && ($st['mode'] & 0170000) === 0100000
        && $st['dev'] === $now['dev'] && $st['ino'] === $now['ino'];
    $data = $same ? stream_get_contents($fh, THEMER_IMAGE_MAX + 1) : false;
    fclose($fh);
    if (!$same) return ['', '', 'the file changed while it was read, try again'];
    if ($data === false) return ['', '', 'could not read that file'];
    if (strlen($data) > THEMER_IMAGE_MAX) return ['', '', 'image too large (>15 MB)'];
    $ext = themer_image_type($data);
    if ($ext === '') return ['', '', 'that file is not an image'];
    return [$data, $ext, ''];
}
