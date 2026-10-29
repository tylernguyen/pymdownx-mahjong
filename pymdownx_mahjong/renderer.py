"""Renderer for Mahjong hands."""

from __future__ import annotations

import html
from typing import Final

from .parser import Hand, Meld, MeldSource, MeldType, Tile
from .sprite import TILE_HEIGHT, TILE_WIDTH, TileSprite

_MELD_NAMES: Final[dict[MeldType, str]] = {
    MeldType.CHI: "Chi",
    MeldType.PON: "Pon",
    MeldType.KAN_OPEN: "Open kan",
    MeldType.KAN_CLOSED: "Closed kan",
    MeldType.KAN_ADDED: "Added kan",
}
_SOURCE_NAMES: Final[dict[MeldSource, str]] = {
    MeldSource.LEFT: "from left",
    MeldSource.ACROSS: "from across",
    MeldSource.RIGHT: "from right",
}


class MahjongRenderer:
    """Renders mahjong hands as HTML with SVG tiles.

    Tile artwork is referenced from a TileSprite. Pass a page-wide sprite to share
    symbols across calls; without one, each call embeds the symbols it uses.

    Configuration options:
        theme: 'light', 'dark', or 'auto'
        closed_kan_style: 'outer' (default) or 'inner'
    """

    DEFAULT_TILE_WIDTH = TILE_WIDTH
    DEFAULT_TILE_HEIGHT = TILE_HEIGHT
    _BACK_TILE_HTML = (
        '<span class="mahjong-tile mahjong-tile-back" role="img" '
        'aria-label="Face-down tile" title="Face-down tile"></span>'
    )

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
        sprite: TileSprite | None = None,
    ) -> str:
        """Render a hand as HTML."""
        page_sprite = sprite
        sprite = sprite or TileSprite()
        parts: list[str] = []

        data_attr = f' data-notation="{html.escape(notation, quote=True)}"' if notation else ""
        theme_class = f" mahjong-theme-{self.theme}" if self.theme in ("light", "dark") else ""
        # A figcaption names the figure; otherwise give it a generic accessible name.
        label_attr = "" if title else ' aria-label="Mahjong hand"'
        parts.append(f'<figure class="{self.css_class}{theme_class}"{data_attr}{label_attr}>')

        if hand.dora_indicators or hand.ura_indicators or hand.waits:
            parts.append('<div class="mahjong-dora-row">')
            if hand.dora_indicators:
                parts.extend(self._render_dora_section(hand.dora_indicators, sprite, "Dora"))
            if hand.ura_indicators:
                parts.extend(self._render_dora_section(hand.ura_indicators, sprite, "Ura", "mahjong-ura"))
            if hand.waits:
                parts.extend(self._render_dora_section(hand.waits, sprite, "Waits", "mahjong-waits"))
            parts.append("</div>")

        parts.append('<div class="mahjong-hand-row">')

        parts.append('<div class="mahjong-hand-left">')
        parts.append('<div class="mahjong-tiles">')
        for tile in hand.closed_tiles:
            parts.append(self._render_tile(tile, sprite))
        parts.append("</div>")
        parts.append("</div>")

        if hand.draw_tile:
            # The visible "Draw" label is CSS generated content, so name the group too.
            parts.append('<div class="mahjong-hand-draw" role="group" aria-label="Draw">')
            parts.append('<div class="mahjong-tiles">')
            parts.append(self._render_tile(hand.draw_tile, sprite))
            parts.append("</div>")
            parts.append("</div>")

        if hand.melds:
            parts.append('<div class="mahjong-hand-melds">')
            parts.append('<div class="mahjong-tiles">')
            for meld in hand.melds:
                parts.append(self._render_meld(meld, sprite))
            parts.append("</div>")
            parts.append("</div>")

        parts.append("</div>")

        if title:
            parts.append(f'<figcaption class="mahjong-caption">{html.escape(title, quote=True)}</figcaption>')

        parts.append("</figure>")

        return self._join(parts, sprite, page_sprite)

    def render_tiles(self, tiles: list[Tile], sprite: TileSprite | None = None) -> str:
        """Render a simple list of tiles as HTML."""
        page_sprite = sprite
        sprite = sprite or TileSprite()
        parts = [f'<span class="{self.css_class}">']
        for tile in tiles:
            parts.append(self._render_tile(tile, sprite))
        parts.append("</span>")
        return self._join(parts, sprite, page_sprite)

    @staticmethod
    def _join(parts: list[str], sprite: TileSprite, page_sprite: TileSprite | None) -> str:
        """Join output parts, embedding the symbols inside the root element unless a
        page-wide sprite emits them."""
        if page_sprite is None:
            parts.insert(1, sprite.render())
        return "".join(parts)

    def _render_dora_section(
        self, tiles: list[Tile], sprite: TileSprite, label: str, extra_class: str = ""
    ) -> list[str]:
        """Render a dora/ura indicator section."""
        cls = f"mahjong-dora {extra_class}".strip()
        parts = [
            f'<div class="{cls}">',
            f'<span class="mahjong-dora-label">{label}</span>',
            '<span class="mahjong-dora-tiles">',
        ]
        for tile in tiles:
            parts.append(self._render_tile(tile, sprite))
        parts.extend(["</span>", "</div>"])
        return parts

    def _render_tile(self, tile: Tile, sprite: TileSprite) -> str:
        """Render a single tile as HTML with an SVG referencing the sprite."""
        if tile.is_back:
            return self._BACK_TILE_HTML

        info = tile.info
        if not info:
            return (
                f'<span class="mahjong-tile mahjong-tile-unknown" data-tile="{tile.notation}" '
                f'role="img" aria-label="Unknown tile">?</span>'
            )

        classes = ["mahjong-tile"]
        if tile.is_rotated:
            classes.append("mahjong-tile-rotated")
        if tile.is_added:
            classes.append("mahjong-tile-added")
        if self.theme in ("light", "dark"):
            classes.append(f"mahjong-theme-{self.theme}")

        class_str = " ".join(classes)
        label = html.escape(info.display_name, quote=True)
        if self.theme == "auto":
            svg_content = (
                f'<span class="mahjong-tile-light">{sprite.use(info.asset_name, "light")}</span>'
                f'<span class="mahjong-tile-dark">{sprite.use(info.asset_name, "dark")}</span>'
            )
        else:
            svg_content = sprite.use(info.asset_name, self.theme)
        return (
            f'<span class="{class_str}" data-tile="{tile.notation}" role="img" '
            f'aria-label="{label}" title="{label}">{svg_content}</span>'
        )

    def _render_meld(self, meld: Meld, sprite: TileSprite) -> str:
        """Render a meld (called tile group)."""
        state = "open" if meld.is_open else "closed"
        class_str = f"mahjong-meld mahjong-meld-{state}"
        label = " ".join(filter(None, [_MELD_NAMES[meld.meld_type], _SOURCE_NAMES.get(meld.source)]))
        parts = [f'<span class="{class_str}" role="group" aria-label="{label}">']

        if meld.meld_type == MeldType.KAN_ADDED:
            parts.extend(self._render_added_kan(meld, sprite))
        else:
            parts.extend(self._render_standard_meld(meld, sprite))

        parts.append("</span>")
        return "".join(parts)

    def _render_added_kan(self, meld: Meld, sprite: TileSprite) -> list[str]:
        """Render an added kan (shouminkan) — stacked pair position depends on source."""
        t = [self._render_tile(tile, sprite) for tile in meld.tiles]
        stack_open = '<span class="mahjong-tile-stack">'
        if meld.tiles[0].is_rotated:
            return [stack_open, t[0], t[3], "</span>", t[1], t[2]]
        if meld.tiles[2].is_rotated:
            return [t[0], t[1], stack_open, t[2], t[3], "</span>"]
        return [t[0], stack_open, t[1], t[3], "</span>", t[2]]

    def _render_standard_meld(self, meld: Meld, sprite: TileSprite) -> list[str]:
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
                    parts.append(self._render_tile(tile, sprite))
            else:
                parts.append(self._render_tile(tile, sprite))

        return parts
