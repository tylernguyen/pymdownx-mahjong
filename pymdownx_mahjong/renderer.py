"""Renderer for Mahjong hands"""

from __future__ import annotations

import functools
import html
import importlib.resources
import re
from typing import Final, Pattern

from .parser import Hand, Meld, MeldType, Tile
from .tiles import TileInfo

# Pre-compiled regex patterns for SVG processing
_RE_XML_DECL: Final[Pattern[str]] = re.compile(r"<\?xml[^?]*\?>")
_RE_WIDTH: Final[Pattern[str]] = re.compile(r'width="[^"]*"')
_RE_HEIGHT: Final[Pattern[str]] = re.compile(r'height="[^"]*"')
# Pattern to find IDs in SVGs
_RE_ID: Final[Pattern[str]] = re.compile(r'id="([^"]+)"')

# Global counter for unique SVG IDs across all renderer instances
_svg_id_counter: int = 0


@functools.lru_cache(maxsize=128)
def _load_svg_from_package(asset_name: str, theme: str) -> str:
    """Load SVG content from package resources with caching.

    This is a module-level cached function to avoid repeated file I/O
    for the same tile assets across multiple renderer instances.

    Args:
        asset_name: Name of the asset (e.g., '1m', 'back')
        theme: Theme to load ('light' or 'dark')

    Returns:
        Raw SVG content string

    Raises:
        FileNotFoundError: If the asset doesn't exist
    """
    assets = importlib.resources.files("pymdownx_mahjong") / "assets" / theme
    svg_file = assets / f"{asset_name}.svg"
    return svg_file.read_text(encoding="utf-8")


class MahjongRenderer:
    """Renders mahjong hands as HTML with inline SVG tiles.

    Configuration options:
        theme: 'light', 'dark', or 'auto'
        closed_kan_style: 'outer' (default) or 'inner'
    """

    DEFAULT_TILE_WIDTH = 45
    DEFAULT_TILE_HEIGHT = 60


    def __init__(
        self,
        theme: str = "light",

        closed_kan_style: str = "outer",
        css_class: str = "mahjong-hand",
    ) -> None:
        """Initialize the renderer.

        Args:
            theme: Color theme ('light', 'dark', or 'auto')
            closed_kan_style: Style for closed kan back tiles:
                'outer' (default) - back tiles on edges (back, front, front, back)
                'inner' - back tiles in middle (front, back, back, front)
            css_class: CSS class for container (internal use)
        """
        self.theme = theme
        self.tile_width = self.DEFAULT_TILE_WIDTH
        self.tile_height = self.DEFAULT_TILE_HEIGHT

        self.css_class = css_class

        self.closed_kan_style = closed_kan_style

    def render(
        self,
        hand: Hand,
        title: str | None = None,
        notation: str | None = None,
    ) -> str:
        """Render a hand as HTML.

        Args:
            hand: Parsed Hand object
            title: Optional caption/title for the hand
            notation: Original notation string for data attribute

        Returns:
            HTML string with rendered tiles
        """
        parts: list[str] = []

        # Container opening
        data_attr = f' data-notation="{self._escape_html(notation)}"' if notation else ""
        parts.append(f'<figure class="{self.css_class}"{data_attr}>')

        # Dora indicators section (above hand, left-aligned, on same line)
        if hand.dora_indicators or hand.uradora_indicators:
            parts.append('<div class="mahjong-dora-row">')

            if hand.dora_indicators:
                parts.append('<div class="mahjong-dora">')
                parts.append('<span class="mahjong-dora-label">Dora:</span>')
                parts.append('<span class="mahjong-dora-tiles">')
                for tile in hand.dora_indicators:
                    parts.append(self._render_tile(tile))
                parts.append("</span>")
                parts.append("</div>")

            if hand.uradora_indicators:
                parts.append('<div class="mahjong-dora mahjong-uradora">')
                parts.append('<span class="mahjong-dora-label">Uradora:</span>')
                parts.append('<span class="mahjong-dora-tiles">')
                for tile in hand.uradora_indicators:
                    parts.append(self._render_tile(tile))
                parts.append("</span>")
                parts.append("</div>")

            parts.append("</div>")

        parts.append('<div class="mahjong-hand-row">')

        # Left section: closed tiles
        parts.append('<div class="mahjong-hand-left">')
        parts.append('<div class="mahjong-tiles">')

        # Render all closed tiles
        for tile in hand.closed_tiles:
            parts.append(self._render_tile(tile))

        parts.append("</div>")
        parts.append("</div>")

        # Draw tile section (only if explicitly specified)
        if hand.draw_tile:
            parts.append('<div class="mahjong-hand-draw">')
            parts.append('<div class="mahjong-tiles">')
            parts.append(self._render_tile(hand.draw_tile))
            parts.append("</div>")
            parts.append("</div>")

        # Melds section (after draw tile)
        if hand.melds:
            parts.append('<div class="mahjong-hand-melds">')
            parts.append('<div class="mahjong-tiles">')
            for meld in hand.melds:
                parts.append(self._render_meld(meld))
            parts.append("</div>")
            parts.append("</div>")

        parts.append("</div>")

        # Caption
        if title:
            parts.append(f'<figcaption class="mahjong-caption">{self._escape_html(title)}</figcaption>')

        parts.append("</figure>")

        return "".join(parts)

    def render_tiles(self, tiles: list[Tile]) -> str:
        """Render a simple list of tiles.

        Args:
            tiles: List of Tile objects

        Returns:
            HTML string with rendered tiles
        """
        parts = [f'<span class="{self.css_class}">']
        for tile in tiles:
            parts.append(self._render_tile(tile))
        parts.append("</span>")
        return "".join(parts)

    def _render_tile(self, tile: Tile) -> str:
        """Render a single tile.

        Args:
            tile: Tile to render

        Returns:
            HTML string for the tile
        """
        info = tile.info
        if not info:
            return f'<span class="mahjong-tile mahjong-tile-unknown" data-tile="{tile.notation}">?</span>'

        classes = ["mahjong-tile"]
        if tile.is_rotated:
            classes.append("mahjong-tile-rotated")
        if tile.is_added:
            classes.append("mahjong-tile-added")
        # Add theme class for explicit themes (not auto)
        if self.theme in ("light", "dark"):
            classes.append(f"mahjong-theme-{self.theme}")

        class_str = " ".join(classes)
        title_attr = f' title="{info.display_name}"'

        if self.theme == "auto":
            svg_content = self._get_themed_svg_content(info)
            return f'<span class="{class_str}" data-tile="{tile.notation}"{title_attr}>{svg_content}</span>'
        else:
            svg_content = self._get_svg_content(info)
            return f'<span class="{class_str}" data-tile="{tile.notation}"{title_attr}>{svg_content}</span>'

    def _render_meld(self, meld: Meld) -> str:
        """Render a meld (called tile group).

        Args:
            meld: Meld to render

        Returns:
            HTML string for the meld
        """
        classes = ["mahjong-meld"]

        if meld.is_open:
            classes.append("mahjong-meld-open")
        else:
            classes.append("mahjong-meld-closed")

        class_str = " ".join(classes)
        parts = [f'<span class="{class_str}">']

        if meld.meld_type == MeldType.KAN_ADDED:
            # Added kan (shouminkan): stacked pair position depends on source
            # Find which tile (0, 1, or 2) is rotated to determine stack position
            if meld.tiles[0].is_rotated:
                # Stack on left: [stack], upright, upright
                parts.append('<span class="mahjong-tile-stack">')
                parts.append(self._render_tile(meld.tiles[0]))
                parts.append(self._render_tile(meld.tiles[3]))
                parts.append("</span>")
                parts.append(self._render_tile(meld.tiles[1]))
                parts.append(self._render_tile(meld.tiles[2]))
            elif meld.tiles[2].is_rotated:
                # Stack on right: upright, upright, [stack]
                parts.append(self._render_tile(meld.tiles[0]))
                parts.append(self._render_tile(meld.tiles[1]))
                parts.append('<span class="mahjong-tile-stack">')
                parts.append(self._render_tile(meld.tiles[2]))
                parts.append(self._render_tile(meld.tiles[3]))
                parts.append("</span>")
            else:
                # Stack in middle (default): upright, [stack], upright
                parts.append(self._render_tile(meld.tiles[0]))
                parts.append('<span class="mahjong-tile-stack">')
                parts.append(self._render_tile(meld.tiles[1]))
                parts.append(self._render_tile(meld.tiles[3]))
                parts.append("</span>")
                parts.append(self._render_tile(meld.tiles[2]))
        else:
            for i, tile in enumerate(meld.tiles):
                # For closed kan, show back tiles based on style setting
                if meld.meld_type == MeldType.KAN_CLOSED:
                    if self.closed_kan_style == "inner":
                        # 'inner': back tiles in middle: front, back, back, front
                        is_back = i in (1, 2)
                    else:
                        # Default 'outer': back tiles on edges: back, front, front, back
                        is_back = i in (0, 3)
                    if is_back:
                        parts.append(self._render_back_tile())
                    else:
                        parts.append(self._render_tile(tile))
                else:
                    parts.append(self._render_tile(tile))

        parts.append("</span>")
        return "".join(parts)

    def _render_back_tile(self) -> str:
        """Render a face-down tile.

        Returns:
            HTML string for a back tile
        """
        return '<span class="mahjong-tile mahjong-tile-back"></span>'

    def _get_svg_content(self, info: TileInfo, theme: str | None = None) -> str:
        """Get the SVG content for a tile, with unique IDs.

        Args:
            info: Tile information
            theme: Optional theme override ('light' or 'dark')

        Returns:
            SVG content string with unique IDs
        """
        theme = theme or (self.theme if self.theme != "auto" else "light")

        # Load and process SVG (package assets use module-level LRU cache)
        svg_content = self._load_svg(info, theme)
        svg_content = self._process_svg(svg_content)

        # Make IDs unique using global counter
        global _svg_id_counter
        _svg_id_counter += 1
        return self._make_ids_unique(svg_content, f"mj{_svg_id_counter}_")

    def _get_themed_svg_content(self, info: TileInfo) -> str:
        """Get SVG content that respects theme switching.

        For 'auto' theme, embeds both light and dark SVGs with CSS to toggle.
        For specific themes, returns a single SVG.

        Args:
            info: Tile information

        Returns:
            SVG content string (possibly wrapped in theme-aware containers)
        """
        if self.theme == "auto":
            # Load both light and dark SVGs
            light_svg = self._get_svg_content(info, "light")
            dark_svg = self._get_svg_content(info, "dark")

            # Wrap each in a container with appropriate display logic
            # CSS will handle the display switching based on theme
            return (
                f'<span class="mahjong-tile-light">{light_svg}</span><span class="mahjong-tile-dark">{dark_svg}</span>'
            )
        else:
            # Single theme - return appropriate SVG
            return self._get_svg_content(info)

    def _load_svg(self, info: TileInfo, theme: str | None = None) -> str:
        """Load SVG content from file.

        Args:
            info: Tile information
            theme: Theme to load ('light' or 'dark')

        Returns:
            Raw SVG content
        """
        theme = theme or (self.theme if self.theme != "auto" else "light")

        # Fall back to package assets (uses module-level LRU cache)
        try:
            return _load_svg_from_package(info.asset_name, theme)
        except (FileNotFoundError, TypeError):
            # Return a placeholder SVG
            return self._placeholder_svg(info)

    def _process_svg(self, svg_content: str) -> str:
        """Process SVG content for inline use.

        - Removes XML declaration
        - Adds sizing attributes

        Args:
            svg_content: Raw SVG content

        Returns:
            Processed SVG content
        """
        # Remove XML declaration
        svg_content = _RE_XML_DECL.sub("", svg_content)

        # Update width/height to our tile size while preserving viewBox
        svg_content = _RE_WIDTH.sub(f'width="{self.tile_width}"', svg_content, count=1)
        svg_content = _RE_HEIGHT.sub(f'height="{self.tile_height}"', svg_content, count=1)

        return svg_content.strip()

    def _make_ids_unique(self, svg_content: str, prefix: str) -> str:
        """Make all IDs in an SVG unique by adding a prefix.

        Args:
            svg_content: SVG content
            prefix: Prefix to add to all IDs

        Returns:
            SVG content with unique IDs
        """
        # Find all IDs in the SVG
        ids = set(_RE_ID.findall(svg_content))

        # Replace each ID and its references
        for old_id in ids:
            new_id = f"{prefix}{old_id}"
            # Replace id="old_id"
            svg_content = svg_content.replace(f'id="{old_id}"', f'id="{new_id}"')
            # Replace href="#old_id" and xlink:href="#old_id"
            svg_content = svg_content.replace(f'href="#{old_id}"', f'href="#{new_id}"')
            # Replace url(#old_id)
            svg_content = svg_content.replace(f"url(#{old_id})", f"url(#{new_id})")

        return svg_content

    def _placeholder_svg(self, info: TileInfo) -> str:
        """Generate a placeholder SVG for missing assets.

        Args:
            info: Tile information

        Returns:
            Placeholder SVG content
        """
        w, h = self.tile_width, self.tile_height
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 300 400">
  <rect width="300" height="400" fill="#f0f0f0" stroke="#ccc" stroke-width="4" rx="20"/>
  <text x="150" y="220" text-anchor="middle" font-size="48" fill="#999">{info.display_name}</text>
</svg>"""

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        return html.escape(text, quote=True)


def render_hand(hand: Hand, **kwargs) -> str:
    """Convenience function to render a hand.

    Args:
        hand: Parsed Hand object
        **kwargs: Renderer options

    Returns:
        HTML string
    """
    renderer = MahjongRenderer(**kwargs)
    return renderer.render(hand)
