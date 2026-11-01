"""Helpers replacing the parts of c:geo's TextUtils used by the connector.

Ported from TextUtils.java (getMatch, matches, replaceWhitespace,
removeControlCharacters, stripHtml). Network.decode is URL decoding.
"""
import html
import re
from html.parser import HTMLParser
from typing import List, Optional, Pattern
from urllib.parse import unquote_plus

# Java's \p{Cntrl} = U+0000-U+001F and U+007F (this includes \n and \t!)
_CNTRL = re.compile(r"[\x00-\x1f\x7f]")
_WS_RUN = re.compile(r"[ \n\r\t]+")
_CONTAINS_HTML = re.compile(
    r"""<(/\s*)?[a-zA-Z]+\s*([a-zA-Z]+\s*=\s*['"][^'"]*['"]\s*)*(/\s*)?>|&#?[a-zA-Z0-9]{1,10};""")
_JAVA_TRIM = "".join(chr(i) for i in range(33))  # String.trim(): everything <= U+0020


def java_trim(s: str) -> str:
    return s.strip(_JAVA_TRIM)


def replace_whitespace(data: Optional[str]) -> Optional[str]:
    """Replace every run of space/\\n/\\r/\\t by one space and drop leading ones.

    Same as TextUtils.replaceWhitespace (only these four characters count).
    """
    if not data:
        return data
    return _WS_RUN.sub(" ", data).lstrip(" ")


def remove_control_characters(data: Optional[str]) -> str:
    """TextUtils.removeControlCharacters: control chars -> space, then trim."""
    return java_trim(_CNTRL.sub(" ", data)) if data else ""


def contains_html(s: Optional[str]) -> bool:
    return bool(s and s.strip() and _CONTAINS_HTML.search(s))


_BLOCK_PARA = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}
_BLOCK_LINE = {"div", "li", "ul", "ol", "tr", "table"}


class _HtmlToText(HTMLParser):
    """Rough equivalent of HtmlCompat.fromHtml(...).toString() (legacy mode)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")
        elif tag in _BLOCK_LINE:
            self._ensure_break("\n")
        elif tag in _BLOCK_PARA:
            self._ensure_break("\n\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_PARA:
            self.parts.append("\n\n")
        elif tag in _BLOCK_LINE:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(_WS_RUN.sub(" ", data))

    def _ensure_break(self, br: str):
        current = "".join(self.parts)
        if current and not current.endswith(br):
            self.parts.append(br)


def strip_html(data: Optional[str]) -> str:
    """TextUtils.stripHtml: plain text unchanged, HTML converted + trailing breaks trimmed."""
    if data is None:
        return ""
    if not contains_html(data):
        return data
    parser = _HtmlToText()
    parser.feed(data)
    parser.close()
    return "".join(parser.parts).rstrip()


def decode(data: Optional[str]) -> str:
    """Network.decode: URL-decode."""
    return unquote_plus(data) if data else ""


def split_whole(s: str, sep: str) -> List[str]:
    """StringUtils.splitByWholeSeparator: adjacent separators count as one."""
    return [p for p in s.split(sep) if p != ""]


def get_match(data: Optional[str], pattern: Pattern, trim: bool = True,
              group: int = 1, default: Optional[str] = None,
              last: bool = False) -> Optional[str]:
    """TextUtils.getMatch: group of the first (or last) match, else `default`.

    Control characters in the result (also \\n, \\t) are replaced by a space;
    `trim` then applies Java's String.trim().
    """
    if data is None:
        return default
    m = pattern.search(data)
    if m is None:
        return default
    result = m.group(group)
    if last:
        for m in pattern.finditer(data):
            result = m.group(group)
    if result is None:
        return default
    result = _CNTRL.sub(" ", result)
    return java_trim(result) if trim else result


def matches(data: Optional[str], pattern: Pattern) -> bool:
    """TextUtils.matches: the pattern is found anywhere in data."""
    return data is not None and pattern.search(data) is not None
