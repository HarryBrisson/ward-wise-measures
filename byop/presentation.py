"""Presentation extras a metric may carry (v1.2): search keywords, extra domains, and an icon glyph.

The icon check is an allowlist, not a blocklist: the glyph is a fragment of plain SVG shapes that a
consumer drops inside its own `<svg viewBox="0 0 20 20">` wrapper with innerHTML, so anything beyond
shapes and their geometry/paint attributes is refused. Consumers run the same check again before
serving the glyph (Penlight: shared/civic_data/icon_svg.py, a copy of this file's icon check).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

ICON_SVG_MAX_CHARS = 2048
KEYWORDS_MAX_CHARS = 300
EXTRA_CATEGORIES_MAX = 4

ICON_ELEMENTS = {"g", "path", "circle", "ellipse", "line", "polyline", "polygon", "rect"}
ICON_ATTRIBUTES = {
    "d", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "y1", "x2", "y2", "width", "height", "points",
    "transform", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray",
    "stroke-opacity", "fill-opacity", "fill-rule", "opacity", "vector-effect",
}
# Geometry, colours ("none", "currentColor", "#333", "var(--surface)") and transforms need nothing more.
# No quotes, colons, semicolons, slashes or angle brackets: no javascript:, no url(), no CSS.
_ICON_VALUE = re.compile(r"^[A-Za-z0-9 .,#%()\-]*$")
_NAMED_HAZARDS = (
    (re.compile(r"<\s*script", re.I), "<script> is not allowed"),
    (re.compile(r"foreignobject", re.I), "<foreignObject> is not allowed"),
    (re.compile(r"(^|[\s\"'/])on[a-z]+\s*=", re.I), "event-handler (on*) attributes are not allowed"),
    (re.compile(r"href", re.I), "href / xlink:href is not allowed"),
)
_SVG_NS = "http://www.w3.org/2000/svg"
KEYWORDS_PATTERN = re.compile(r"^[a-z0-9 .,%$&'+/-]*$")


def icon_svg_problems(markup: Any) -> list[str]:
    """Why `markup` isn't a safe inner-SVG glyph (empty = fine)."""
    if not isinstance(markup, str) or not markup.strip():
        return ["icon_svg must be a non-empty string of SVG shapes"]
    if len(markup) > ICON_SVG_MAX_CHARS:
        return [f"icon_svg is {len(markup)} characters; the cap is {ICON_SVG_MAX_CHARS}"]
    problems = [message for pattern, message in _NAMED_HAZARDS if pattern.search(markup)]
    if re.search(r"<[!?]|&", markup):
        problems.append("icon_svg may not contain comments, CDATA, doctypes, processing instructions or entities")
    if problems:
        return problems
    try:
        root = ET.fromstring(f'<svg xmlns="{_SVG_NS}">{markup}</svg>')
    except ET.ParseError as error:
        return [f"icon_svg is not well-formed SVG markup: {error}"]
    for element in root.iter():
        tag = element.tag.split("}", 1)[-1]
        if element is not root and (not element.tag.startswith(f"{{{_SVG_NS}}}") or tag not in ICON_ELEMENTS):
            problems.append(f"icon_svg element <{tag}> is not allowed (use {', '.join(sorted(ICON_ELEMENTS))})")
            continue
        if (element.text or "").strip() or (element is not root and (element.tail or "").strip()):
            problems.append("icon_svg may not contain text")
        if element is root:
            continue
        for name, value in element.attrib.items():
            local = name.split("}", 1)[-1]
            if name.startswith("{") or local not in ICON_ATTRIBUTES:
                problems.append(f"icon_svg attribute {local!r} on <{tag}> is not allowed")
            elif not _ICON_VALUE.match(value) or "url(" in value.lower() or "expression(" in value.lower():
                problems.append(f"icon_svg attribute {local}={value!r} has characters a glyph doesn't need")
    return sorted(set(problems), key=problems.index)


def keywords_problems(value: Any) -> list[str]:
    if not isinstance(value, str):
        return ["keywords must be a string of space-separated words"]
    problems = []
    if len(value) > KEYWORDS_MAX_CHARS:
        problems.append(f"keywords is {len(value)} characters; the cap is {KEYWORDS_MAX_CHARS}")
    if value != value.lower():
        problems.append("keywords must be lowercase")
    if not KEYWORDS_PATTERN.match(value.lower()):
        problems.append("keywords may hold letters, digits, spaces and . , % $ & ' + / - only")
    return problems


def extra_categories_problems(value: Any, domains: set[str], category: str | None = None) -> list[str]:
    if not (isinstance(value, list) and all(isinstance(c, str) for c in value)):
        return ["extra_categories must be a list of Penlight domain slugs"]
    problems = []
    if len(value) > EXTRA_CATEGORIES_MAX:
        problems.append(f"extra_categories lists {len(value)} domains; the cap is {EXTRA_CATEGORIES_MAX}")
    if len(set(value)) != len(value):
        problems.append("extra_categories repeats a domain")
    for slug in value:
        if slug not in domains:
            problems.append(f"extra_categories: {slug!r} is not a Penlight domain")
        elif slug == category:
            problems.append(f"extra_categories: {slug!r} is already the metric's category")
    return problems
