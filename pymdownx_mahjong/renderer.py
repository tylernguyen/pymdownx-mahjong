"""Renderer for Mahjong hands."""

from __future__ import annotations

import functools
import html
import importlib.resources
import itertools
import re
from typing import Final

from .parser import Hand, Meld, MeldType, Tile
from .tiles import TileInfo

_RE_XML_DECL: Final[re.Pattern[str]] = re.compile(r"<\?xml[^?]*\?>")
_RE_WIDTH: Final[re.Pattern[str]] = re.compile(r'width="[^"]*"')
_RE_HEIGHT: Final[re.Pattern[str]] = re.compile(r'height="[^"]*"')
_RE_ID: Final[re.Pattern[str]] = re.compile(r'id="([^"]+)"')

_svg_id_counter = itertools.count(1)


@functools.lru_cache(maxsize=128)
def _load_and_process_svg(asset_name: str, theme: str) -> str:
    """Load SVG from package resources, strip XML declaration, and set tile dimensions."""
    assets = importlib.resources.files("pymdownx_mahjong") / "assets" / theme
    svg_content = (assets / f"{asset_name}.svg").read_text(encoding="utf-8")
    svg_content = _RE_XML_DECL.sub("", svg_content)
    svg_content = _RE_WIDTH.sub(f'width="{MahjongRenderer.DEFAULT_TILE_WIDTH}"', svg_content, count=1)
    svg_content = _RE_HEIGHT.sub(f'height="{MahjongRenderer.DEFAULT_TILE_HEIGHT}"', svg_content, count=1)
    return svg_content.strip()


class MahjongRenderer:
    """Renders mahjong hands as HTML with inline SVG tiles.

    Configuration options:
        theme: 'light', 'dark', or 'auto'
        closed_kan_style: 'outer' (default) or 'inner'
    """

    DEFAULT_TILE_WIDTH = 45
    DEFAULT_TILE_HEIGHT = 60
    _BACK_TILE_HTML = '<span class="mahjong-tile mahjong-tile-back"></span>'

    def __init__(
        self,
        theme: str = "light",
        closed_kan_style: str = "outer",
        css_class: str = "mahjong-hand",
    ) -> None:
        self.theme = theme
        self.css_class = css_class
        self.closed_kan_style = closed_kan_style

    def render(
        self,
        hand: Hand,
        title: str | None = None,
        notation: str | None = None,
    ) -> str:
        """Render a hand as HTML."""
        parts: list[str] = []

        data_attr = f' data-notation="{html.escape(notation, quote=True)}"' if notation else ""
        parts.append(f'<figure class="{self.css_class}"{data_attr}>')

        if hand.dora_indicators or hand.uradora_indicators:
            parts.append('<div class="mahjong-dora-row">')
            if hand.dora_indicators:
                parts.extend(self._render_dora_section(hand.dora_indicators, "Dora:"))
            if hand.uradora_indicators:
                parts.extend(self._render_dora_section(hand.uradora_indicators, "Uradora:", "mahjong-uradora"))
            parts.append("</div>")

        parts.append('<div class="mahjong-hand-row">')

        parts.append('<div class="mahjong-hand-left">')
        parts.append('<div class="mahjong-tiles">')
        for tile in hand.closed_tiles:
            parts.append(self._render_tile(tile))
        parts.append("</div>")
        parts.append("</div>")

        if hand.draw_tile:
            parts.append('<div class="mahjong-hand-draw">')
            parts.append('<div class="mahjong-tiles">')
            parts.append(self._render_tile(hand.draw_tile))
            parts.append("</div>")
            parts.append("</div>")

        if hand.melds:
            parts.append('<div class="mahjong-hand-melds">')
            parts.append('<div class="mahjong-tiles">')
            for meld in hand.melds:
                parts.append(self._render_meld(meld))
            parts.append("</div>")
            parts.append("</div>")

        parts.append("</div>")

        if title:
            parts.append(f'<figcaption class="mahjong-caption">{html.escape(title, quote=True)}</figcaption>')

        parts.append("</figure>")

        return "".join(parts)

    def render_tiles(self, tiles: list[Tile]) -> str:
        """Render a simple list of tiles as HTML."""
        parts = [f'<span class="{self.css_class}">']
        for tile in tiles:
            parts.append(self._render_tile(tile))
        parts.append("</span>")
        return "".join(parts)

    def _render_dora_section(self, tiles: list[Tile], label: str, extra_class: str = "") -> list[str]:
        """Render a dora/uradora indicator section."""
        cls = f"mahjong-dora {extra_class}".strip()
        parts = [f'<div class="{cls}">',
                 f'<span class="mahjong-dora-label">{label}</span>',
                 '<span class="mahjong-dora-tiles">']
        for tile in tiles:
            parts.append(self._render_tile(tile))
        parts.extend(["</span>", "</div>"])
        return parts

    def _render_tile(self, tile: Tile) -> str:
        """Render a single tile as HTML with inline SVG."""
        info = tile.info
        if not info:
            return f'<span class="mahjong-tile mahjong-tile-unknown" data-tile="{tile.notation}">?</span>'

        classes = ["mahjong-tile"]
        if tile.is_rotated:
            classes.append("mahjong-tile-rotated")
        if tile.is_added:
            classes.append("mahjong-tile-added")
        if self.theme in ("light", "dark"):
            classes.append(f"mahjong-theme-{self.theme}")

        class_str = " ".join(classes)
        title_attr = f' title="{info.display_name}"'
        svg_content = self._get_themed_svg_content(info) if self.theme == "auto" else self._get_svg_content(info)
        return f'<span class="{class_str}" data-tile="{tile.notation}"{title_attr}>{svg_content}</span>'

    def _render_meld(self, meld: Meld) -> str:
        """Render a meld (called tile group)."""
        state = "open" if meld.is_open else "closed"
        class_str = f"mahjong-meld mahjong-meld-{state}"
        parts = [f'<span class="{class_str}">']

        if meld.meld_type == MeldType.KAN_ADDED:
            parts.extend(self._render_added_kan(meld))
        else:
            parts.extend(self._render_standard_meld(meld))

        parts.append("</span>")
        return "".join(parts)

    def _render_added_kan(self, meld: Meld) -> list[str]:
        """Render an added kan (shouminkan) — stacked pair position depends on source."""
        parts: list[str] = []
        if meld.tiles[0].is_rotated:
            parts.append('<span class="mahjong-tile-stack">')
            parts.append(self._render_tile(meld.tiles[0]))
            parts.append(self._render_tile(meld.tiles[3]))
            parts.append("</span>")
            parts.append(self._render_tile(meld.tiles[1]))
            parts.append(self._render_tile(meld.tiles[2]))
        elif meld.tiles[2].is_rotated:
            parts.append(self._render_tile(meld.tiles[0]))
            parts.append(self._render_tile(meld.tiles[1]))
            parts.append('<span class="mahjong-tile-stack">')
            parts.append(self._render_tile(meld.tiles[2]))
            parts.append(self._render_tile(meld.tiles[3]))
            parts.append("</span>")
        else:
            parts.append(self._render_tile(meld.tiles[0]))
            parts.append('<span class="mahjong-tile-stack">')
            parts.append(self._render_tile(meld.tiles[1]))
            parts.append(self._render_tile(meld.tiles[3]))
            parts.append("</span>")
            parts.append(self._render_tile(meld.tiles[2]))

        return parts

    def _render_standard_meld(self, meld: Meld) -> list[str]:
        """Render a standard meld (non-added kan)."""
        parts: list[str] = []
        for i, tile in enumerate(meld.tiles):
            if meld.meld_type == MeldType.KAN_CLOSED:
                if self.closed_kan_style == "inner":
                    is_back = i in (1, 2)  # front, back, back, front
                else:
                    is_back = i in (0, 3)  # back, front, front, back
                if is_back:
                    parts.append(self._BACK_TILE_HTML)
                else:
                    parts.append(self._render_tile(tile))
            else:
                parts.append(self._render_tile(tile))

        return parts

    def _get_svg_content(self, info: TileInfo, theme: str | None = None) -> str:
        """Load processed SVG content for a tile with unique IDs."""
        theme = theme or (self.theme if self.theme != "auto" else "light")

        try:
            svg_content = _load_and_process_svg(info.asset_name, theme)
        except (FileNotFoundError, TypeError):
            svg_content = self._placeholder_svg(info)

        return self._make_ids_unique(svg_content, f"mj{next(_svg_id_counter)}_")

    def _get_themed_svg_content(self, info: TileInfo) -> str:
        """Get both light and dark SVGs wrapped in theme-aware containers."""
        light_svg = self._get_svg_content(info, "light")
        dark_svg = self._get_svg_content(info, "dark")
        return f'<span class="mahjong-tile-light">{light_svg}</span><span class="mahjong-tile-dark">{dark_svg}</span>'

    def _make_ids_unique(self, svg_content: str, prefix: str) -> str:
        """Add a prefix to all IDs and their references in an SVG."""
        ids = set(_RE_ID.findall(svg_content))

        for old_id in ids:
            new_id = f"{prefix}{old_id}"
            svg_content = svg_content.replace(f'id="{old_id}"', f'id="{new_id}"')
            svg_content = svg_content.replace(f'href="#{old_id}"', f'href="#{new_id}"')
            svg_content = svg_content.replace(f"url(#{old_id})", f"url(#{new_id})")

        return svg_content

    def _placeholder_svg(self, info: TileInfo) -> str:
        """Generate a placeholder SVG for missing assets."""
        w, h = self.DEFAULT_TILE_WIDTH, self.DEFAULT_TILE_HEIGHT
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 300 400">'
            f'<rect width="300" height="400" fill="#f0f0f0" stroke="#ccc" stroke-width="4" rx="20"/>'
            f'<text x="150" y="220" text-anchor="middle" font-size="48" fill="#999">{info.display_name}</text>'
            f'</svg>'
        )
