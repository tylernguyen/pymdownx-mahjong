"""Per-page SVG sprite for tile artwork.

Each tile's SVG is emitted once per page as a ``<symbol>`` and every tile references it
with ``<use>``, instead of inlining the full artwork for every tile. Symbol IDs are
derived from the theme and asset name, so output is deterministic across builds.
"""

from __future__ import annotations

import functools
import importlib.resources
import re
from typing import Final

_RE_XML_DECL: Final[re.Pattern[str]] = re.compile(r"<\?xml[^?]*\?>")
_RE_ROOT: Final[re.Pattern[str]] = re.compile(r"<svg\b([^>]*?)(/?)>")
_RE_VIEWBOX: Final[re.Pattern[str]] = re.compile(r'viewBox="([^"]*)"')
_RE_ID: Final[re.Pattern[str]] = re.compile(r'\bid="([^"]+)"')

_DEFAULT_VIEWBOX: Final[str] = "0 0 300 400"
SPRITE_CLASS: Final[str] = "mahjong-sprite"
# Hidden without display:none, which can stop referenced content from rendering.
SPRITE_STYLE: Final[str] = "position:absolute;width:0;height:0;overflow:hidden"

TILE_WIDTH: Final[int] = 45
TILE_HEIGHT: Final[int] = 60


def symbol_id(asset_name: str, theme: str) -> str:
    return f"mj-{theme}-{asset_name}"


@functools.cache
def load_symbol(asset_name: str, theme: str) -> str:
    """Load a tile SVG from package resources and convert it to a ``<symbol>``."""
    sid = symbol_id(asset_name, theme)
    assets = importlib.resources.files("pymdownx_mahjong") / "assets" / theme
    try:
        svg = (assets / f"{asset_name}.svg").read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        return _placeholder_symbol(sid, asset_name)

    svg = _RE_XML_DECL.sub("", svg).strip()
    root = _RE_ROOT.search(svg)
    if root is None:
        return _placeholder_symbol(sid, asset_name)

    viewbox_match = _RE_VIEWBOX.search(root.group(1))
    viewbox = viewbox_match.group(1) if viewbox_match else _DEFAULT_VIEWBOX
    # Self-closing root (<svg .../>) is an empty tile face, e.g. the white dragon.
    body = "" if root.group(2) else svg[root.end() : svg.rindex("</svg>")]

    # The root's xmlns:xlink declaration is dropped, so use the SVG 2 href attribute.
    body = body.replace("xlink:href=", "href=")

    # Namespace internal IDs by symbol so they can't collide with other tiles on the page.
    for old_id in set(_RE_ID.findall(body)):
        new_id = f"{sid}-{old_id}"
        body = body.replace(f'id="{old_id}"', f'id="{new_id}"')
        body = body.replace(f'href="#{old_id}"', f'href="#{new_id}"')
        body = body.replace(f"url(#{old_id})", f"url(#{new_id})")

    return f'<symbol id="{sid}" viewBox="{viewbox}">{body}</symbol>'


def _placeholder_symbol(sid: str, asset_name: str) -> str:
    """Generate a placeholder symbol for missing assets."""
    return (
        f'<symbol id="{sid}" viewBox="{_DEFAULT_VIEWBOX}">'
        f'<rect width="300" height="400" fill="#f0f0f0" stroke="#ccc" stroke-width="4" rx="20"/>'
        f'<text x="150" y="220" text-anchor="middle" font-size="48" fill="#999">{asset_name}</text>'
        f"</symbol>"
    )


class TileSprite:
    """Collects the tile symbols used on a page and renders them as one hidden SVG."""

    def __init__(self) -> None:
        self._symbols: dict[str, str] = {}

    def use(self, asset_name: str, theme: str) -> str:
        """Register a tile's symbol and return an SVG that references it."""
        sid = symbol_id(asset_name, theme)
        if sid not in self._symbols:
            self._symbols[sid] = load_symbol(asset_name, theme)
        return (
            f'<svg width="{TILE_WIDTH}" height="{TILE_HEIGHT}" aria-hidden="true" focusable="false">'
            f'<use href="#{sid}"/></svg>'
        )

    def render(self) -> str:
        """Render all registered symbols as a hidden SVG, or an empty string if none were used."""
        if not self._symbols:
            return ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" class="{SPRITE_CLASS}" aria-hidden="true" '
            f'focusable="false" style="{SPRITE_STYLE}">{"".join(self._symbols.values())}</svg>'
        )

    def render_symbols(self) -> str:
        """Render all registered symbols in a bare SVG, for the caller to hide and place."""
        if not self._symbols:
            return ""
        return f'<svg xmlns="http://www.w3.org/2000/svg">{"".join(self._symbols.values())}</svg>'

    def reset(self) -> None:
        self._symbols.clear()
