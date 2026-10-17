<?php
/* Theme stylesheet rules, used by the settings page (imports, store) and by
 * migrate-assets.php at boot (themes stored on flash). test/test_css_rules.py
 * runs this file against the attack corpus. */

/* What a theme stylesheet may contain: the PHP side of scripts/css_rules.py,
 * held to the same corpus by test/test_css_rules.py. A theme only sets colours,
 * sizes and fonts, so everything that can make the browser fetch is refused:
 * any backslash (CSS escapes turn `\68ttps` into `https` and `@\69mport` into
 * `@import`), resource functions like url() and image-set(), and every at-rule
 * except @media and @supports. A fetch is what makes a theme dangerous: an
 * attribute selector on Unraid's hidden csrf_token input could leak the token
 * one character per request. Returns the first broken rule, "" when acceptable. */
function themer_css_violation($css) {
    if (strlen($css) > 512 * 1024)   return "file too large (>512 KB)";
    // The checks only see what the browser sees if both read the same text. A
    // UTF-16 file (BOM FF FE) puts a NUL between every letter, so `url(` never
    // matches, yet the browser decodes it by its BOM and loads the URLs.
    if (preg_match('//u', $css) !== 1) return "is not valid UTF-8 (a UTF-16 file would hide its content from these checks)";
    if (strpos($css, "\0") !== false) return "contains a NUL byte";
    if (strpos($css, '\\') !== false) return "contains a backslash (CSS escapes are not allowed)";
    // only what can start an HTML tag; a bare < is a media range (`width < 800px`)
    if (preg_match('/<[a-zA-Z\/!?]/', $css) !== 0) return "contains markup (<tag)";
    // a regex that fails (backtrack limit) returns false/null, which must count
    // as a hit: "no match" would let the stylesheet through unchecked
    $code  = preg_replace('~/\*.*?\*/~s', '', $css);
    if ($code === null) return "could not be checked";
    $fetch = '/(?<![\w-])(?:-[a-z]+-)?(?:url|image-set|image|cross-fade|element|src|attr|paint)\s*\(/i';
    // both spellings: a comment can hide a name from one view but not the other
    if (preg_match($fetch, $css) !== 0 || preg_match($fetch, $code) !== 0)
        return "loads a resource (url(), image-set() or similar)";
    if (preg_match('/@(?!(?:media|supports)\b)/i', $code) !== 0)
        return "contains an at-rule other than @media or @supports";
    $legacy = [
        '/javascript\s*:/i'  => "contains a javascript: URI",
        '/expression\s*\(/i' => "contains a CSS expression()",
        '/behaviou?r\s*:/i'  => "contains a CSS behavior:",
        '/-moz-binding/i'    => "contains -moz-binding",
    ];
    foreach ($legacy as $re => $why) {
        if (preg_match($re, $css) !== 0) return $why;
    }
    return "";
}

/* Validate imported CSS before we ever write it to disk. Returns [clean, error]. */
function themer_sanitize_css($css) {
    $css = (string) $css;
    if (trim($css) === '') return ["", "empty or download failed"];
    $why = themer_css_violation($css);
    return $why === "" ? [$css, ""] : ["", $why];
}
