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
 * document, no href, text content only in <text>, <tspan>, <title> and <desc>
 * (it is escaped on output, so it can only ever be text). A style
 * attribute is not kept as CSS: each declaration that names an allowed
 * presentation attribute with a safe value becomes that attribute, the rest
 * is dropped, so `style="fill:none;stroke:currentColor"` still draws.
 * Anything else is dropped, and the result is serialised fresh, so what gets
 * stored is only what passed the allowlist.
 *
 * Returns [clean, error]. test/test_svg_rules.py runs it against an attack
 * corpus and every bundled icon. */

const THEMER_SVG_NS = 'http://www.w3.org/2000/svg';

function themer_svg_allowed_elements() {
    return array_flip(['svg', 'g', 'path', 'circle', 'ellipse', 'line', 'polyline',
        'polygon', 'rect', 'defs', 'title', 'desc', 'linearGradient', 'radialGradient',
        'stop', 'clipPath', 'mask', 'symbol', 'text', 'tspan']);
}

function themer_svg_allowed_attributes() {
    return array_flip(['id', 'd', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx',
        'ry', 'fx', 'fy', 'width', 'height', 'viewBox', 'preserveAspectRatio', 'points',
        'transform', 'fill', 'fill-rule', 'fill-opacity', 'stroke', 'stroke-width',
        'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-dasharray',
        'stroke-dashoffset', 'stroke-opacity', 'opacity', 'offset', 'stop-color',
        'stop-opacity', 'gradientUnits', 'gradientTransform', 'spreadMethod',
        'clip-path', 'clip-rule', 'clipPathUnits', 'mask', 'maskUnits',
        'maskContentUnits', 'color', 'version', 'dx', 'dy', 'rotate', 'textLength',
        'lengthAdjust', 'font-family', 'font-size', 'font-weight', 'font-style',
        'font-variant', 'font-stretch', 'text-anchor', 'dominant-baseline',
        'alignment-baseline', 'baseline-shift', 'letter-spacing', 'word-spacing',
        'text-decoration', 'writing-mode']);
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

// Turn a style attribute into plain presentation attributes. CSS gives the
// style declaration precedence over an attribute of the same name, so it wins.
function themer_svg_style_to_attrs(DOMElement $el, $style, $attrs) {
    foreach (explode(';', $style) as $decl) {
        $parts = explode(':', $decl, 2);
        if (count($parts) !== 2) continue;
        $prop = strtolower(trim($parts[0]));
        $val  = trim(preg_replace('/\s*!important\s*$/i', '', $parts[1]));
        if ($prop === 'id' || !isset($attrs[$prop]) || $val === '' || !themer_svg_value_ok($val)) continue;
        $el->setAttribute($prop, $val);
    }
}

// Clean the attributes of one element in place.
function themer_svg_clean_attrs(DOMElement $el, $attrs) {
    foreach (iterator_to_array($el->attributes) as $a) {
        if ($a->namespaceURI === null && $a->localName === 'style') {
            $el->removeAttributeNode($a);
            themer_svg_style_to_attrs($el, $a->value, $attrs);
        }
    }
    foreach (iterator_to_array($el->attributes) as $a) {
        // a namespaced attribute (xlink:href, xml:base, foreign prefixes)
        // is never needed for drawing
        if ($a->namespaceURI !== null || !isset($attrs[$a->localName]) || !themer_svg_value_ok($a->value))
            $el->removeAttributeNode($a);
    }
}

function themer_sanitize_svg($svg, $max = 65536) {
    $svg = (string) $svg;
    if (trim($svg) === '')  return ["", "empty or download failed"];
    if (strlen($svg) > $max) return ["", "too large (>" . intdiv($max, 1024) . " KB)"];
    // entities are how XML smuggles content past a parser; no DTD at all
    if (preg_match('/<!(DOCTYPE|ENTITY)/i', $svg)) return ["", "contains a DOCTYPE or entity"];

    $doc = themer_svg_parse($svg);
    if (!$doc) return ["", "not a well-formed SVG document"];
    // the byte check above misses a DOCTYPE in UTF-16; the parsed document does not
    if ($doc->doctype !== null) return ["", "contains a DOCTYPE or entity"];
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
    $text_ok = ['title' => 1, 'desc' => 1, 'text' => 1, 'tspan' => 1];

    // collect first, then remove: removing while iterating a live list skips nodes
    $drop = [];
    $walk = function (DOMNode $node) use (&$walk, &$drop, $elements, $attrs, $text_ok) {
        foreach (iterator_to_array($node->childNodes) as $child) {
            if ($child instanceof DOMElement) {
                if ($child->namespaceURI !== THEMER_SVG_NS || !isset($elements[$child->localName])) {
                    $drop[] = $child;
                    continue;
                }
                themer_svg_clean_attrs($child, $attrs);
                $walk($child);
            } elseif ($child instanceof DOMText && !($child instanceof DOMCdataSection)) {
                if (!isset($text_ok[$node->localName ?? ''])) $drop[] = $child;
            } else {
                // comments, processing instructions, CDATA, entity references
                $drop[] = $child;
            }
        }
    };
    themer_svg_clean_attrs($root, $attrs);
    $walk($root);
    foreach ($drop as $n) {
        if ($n->parentNode) $n->parentNode->removeChild($n);
    }

    // serialise fresh: only the root element, so no prolog or stray nodes survive
    $clean = $doc->saveXML($root);
    if ($clean === false || $clean === '') return ["", "could not be cleaned"];
    return [$clean, ""];
}
