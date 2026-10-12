"""
css_rules.py: what a theme stylesheet may contain.

One definition for the CI gate (sanitize_css.py), the submission bot and the
publish bot. The plugin enforces the same rules in PHP (themer_css_violation in
include/css.php); test/test_css_rules.py runs both against one corpus so the
two cannot drift apart.

A theme only sets colours, sizes and fonts on existing selectors. Everything
that can make the browser fetch something is refused, in every spelling the
CSS tokenizer accepts:
  - any backslash: CSS escapes turn `\\68ttps` into `https` and `@\\69mport`
    into `@import`, so with escapes allowed no name check can be trusted
  - resource functions: url(), image-set() and their relatives
  - every at-rule except @media and @supports (@import, @font-face, ...),
    which also refuses an @ inside a string; telling the two apart would
    need a CSS tokenizer in two languages, for a case no theme has
A fetch is the dangerous part: with an attribute selector on Unraid's hidden
csrf_token input, a theme could leak the token one character per request.
"""
import re

MAX_BYTES = 512 * 1024

COMMENT = re.compile(r"/\*.*?\*/", re.S)
FETCH = re.compile(r"(?<![\w-])(?:-[a-z]+-)?(?:url|image-set|image|cross-fade|element|src|attr|paint)\s*\(", re.I)
# only what can start an HTML tag; a bare < is a media range (`width < 800px`)
MARKUP = re.compile(r"<[a-zA-Z/!?]")
AT_RULE = re.compile(r"@(?!(?:media|supports)\b)", re.I)
LEGACY = [
    (re.compile(r"javascript\s*:", re.I), "contains a javascript: URI"),
    (re.compile(r"expression\s*\(", re.I), "contains a CSS expression()"),
    (re.compile(r"behaviou?r\s*:", re.I), "contains a CSS behavior:"),
    (re.compile(r"-moz-binding", re.I), "contains -moz-binding"),
]


def violations(css):
    """Every rule the stylesheet breaks, empty when it is acceptable."""
    errs = []
    if len(css.encode("utf-8")) > MAX_BYTES:
        errs.append("file too large (>512 KB)")
    if "\\" in css:
        errs.append("contains a backslash (CSS escapes are not allowed)")
    if MARKUP.search(css):
        errs.append("contains markup (<tag)")
    code = COMMENT.sub("", css)
    # both spellings: a comment can hide a name from one view but not the other
    if FETCH.search(css) or FETCH.search(code):
        errs.append("loads a resource (url(), image-set() or similar)")
    if AT_RULE.search(code):
        errs.append("contains an at-rule other than @media or @supports")
    for rx, why in LEGACY:
        if rx.search(css):
            errs.append(why)
    return errs
