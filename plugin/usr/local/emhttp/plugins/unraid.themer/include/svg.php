<?php
/* SVG sanitiser for everything a user can bring in as SVG: icon overrides
 * (pasted, uploaded, by URL) and the logo and background image.
 *
 * These files are served from the webGui's own origin, so a script inside one
 * runs with the admin's session when the file is opened directly. A blocklist
 * of regexes was beaten by namespace prefixes (<s:script>) and entity-encoded
 * values (jav&#x61;script:). This parses the document instead and rebuilds it
 * from an allowlist: only SVG-namespace drawing elements, only un-namespaced
 * presentation attributes, url() only as a reference to an id in the same
 * document, no style, no href, no text content outside <title>/<desc>.
 * Anything else is dropped, and the result is serialised fresh, so what gets
 * stored is only what passed the allowlist.
 *
 * Returns [clean, error]. test/test_svg_rules.py runs it against an attack
 * corpus and every bundled icon. */

const THEMER_SVG_NS = 'http://www.w3.org/2000/svg';

function themer_svg_allowed_elements() {
    return array_flip(['svg', 'g', 'path', 'circle', 'ellipse', 'line', 'polyline',
        'polygon', 'rect', 'defs', 'title', 'desc', 'linearGradient', 'radialGradient',
        'stop', 'clipPath', 'mask', 'symbol']);
}

function themer_svg_allowed_attributes() {
    return array_flip(['id', 'd', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx',
        'ry', 'fx', 'fy', 'width', 'height', 'viewBox', 'preserveAspectRatio', 'points',
        'transform', 'fill', 'fill-rule', 'fill-opacity', 'stroke', 'stroke-width',
        'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-dasharray',
        'stroke-dashoffset', 'stroke-opacity', 'opacity', 'offset', 'stop-color',
        'stop-opacity', 'gradientUnits', 'gradientTransform', 'spreadMethod',
        'clip-path', 'clip-rule', 'clipPathUnits', 'mask', 'maskUnits',
        'maskContentUnits', 'color', 'version']);
}

// An attribute value may reference another element of the same document
// (fill="url(#grad)") but never load anything or carry a scheme.
function themer_svg_value_ok($value) {
    $v = strtolower(preg_replace('/\s+/', '', $value));
    if (strpos($v, 'url(') !== false) {
        return preg_match('/^url\(#[a-z0-9_.:-]+\)$/', $v) === 1;
    }
    return strpos($v, ':') === false && strpos($v, '\\') === false && strpos($v, '<') === false;
}

// LIBXML_NONET: never fetch anything; no LIBXML_NOENT, so entities stay unexpanded
function themer_svg_parse($xml) {
    $prev = libxml_use_internal_errors(true);
    $doc = new DOMDocument();
    $ok = $doc->loadXML($xml, LIBXML_NONET | LIBXML_COMPACT);
    libxml_clear_errors();
    libxml_use_internal_errors($prev);
    return ($ok && $doc->documentElement) ? $doc : null;
}

function themer_sanitize_svg($svg, $max = 65536) {
    $svg = (string) $svg;
    if (trim($svg) === '')  return ["", "empty or download failed"];
    if (strlen($svg) > $max) return ["", "too large (>" . intdiv($max, 1024) . " KB)"];
    // entities are how XML smuggles content past a parser; no DTD at all
    if (preg_match('/<!(DOCTYPE|ENTITY)/i', $svg)) return ["", "contains a DOCTYPE or entity"];

    $doc = themer_svg_parse($svg);
    if (!$doc) return ["", "not a well-formed SVG document"];
    $root = $doc->documentElement;
    // inline <svg> copied out of a web page has no xmlns; as a file it would not
    // even render. Give it the SVG namespace and clean it like any other.
    if ($root->namespaceURI === null && $root->localName === 'svg') {
        $doc = themer_svg_parse(preg_replace('/<svg\b/i', '<svg xmlns="' . THEMER_SVG_NS . '"', $svg, 1));
        if (!$doc) return ["", "not a well-formed SVG document"];
        $root = $doc->documentElement;
    }
    if ($root->namespaceURI !== THEMER_SVG_NS || $root->localName !== 'svg')
        return ["", "not an <svg> document"];

    $elements = themer_svg_allowed_elements();
    $attrs = themer_svg_allowed_attributes();
    $text_ok = ['title' => 1, 'desc' => 1];

    // collect first, then remove: removing while iterating a live list skips nodes
    $drop = [];
    $walk = function (DOMNode $node) use (&$walk, &$drop, $elements, $attrs, $text_ok) {
        foreach (iterator_to_array($node->childNodes) as $child) {
            if ($child instanceof DOMElement) {
                if ($child->namespaceURI !== THEMER_SVG_NS || !isset($elements[$child->localName])) {
                    $drop[] = $child;
                    continue;
                }
                foreach (iterator_to_array($child->attributes) as $a) {
                    // a namespaced attribute (xlink:href, xml:base, foreign prefixes)
                    // is never needed for drawing
                    if ($a->namespaceURI !== null || !isset($attrs[$a->localName])
                        || !themer_svg_value_ok($a->value)) {
                        $child->removeAttributeNode($a);
                    }
                }
                $walk($child);
            } elseif ($child instanceof DOMText && !($child instanceof DOMCdataSection)) {
                if (!isset($text_ok[$node->localName ?? ''])) $drop[] = $child;
            } else {
                // comments, processing instructions, CDATA, entity references
                $drop[] = $child;
            }
        }
    };
    foreach (iterator_to_array($root->attributes) as $a) {
        if ($a->namespaceURI !== null || !isset($attrs[$a->localName]) || !themer_svg_value_ok($a->value))
            $root->removeAttributeNode($a);
    }
    $walk($root);
    foreach ($drop as $n) {
        if ($n->parentNode) $n->parentNode->removeChild($n);
    }

    // serialise fresh: only the root element, so no prolog or stray nodes survive
    $clean = $doc->saveXML($root);
    if ($clean === false || $clean === '') return ["", "could not be cleaned"];
    return [$clean, ""];
}
