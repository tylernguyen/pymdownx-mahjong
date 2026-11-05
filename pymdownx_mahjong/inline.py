"""Inline processor for Mahjong tile notation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from markdown.inlinepatterns import InlineProcessor

from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer

if TYPE_CHECKING:
    import re

    from markdown import Markdown

    from .sprite import TileSprite

# Matches :123m:, :1z:, :Xz:, :1234567Xz: etc. — rank+suit groups where a rank is a
# digit or X (X = a face-down tile, e.g. Xz). An ASCII letter or digit on either side means
# it's ordinary text like 10:30m:15, not tiles; \w would also reject tiles beside CJK text.
INLINE_TILE_PATTERN: Final[str] = r"(?<![0-9A-Za-z]):((?:[0-9X]+[mpsz])+):(?![0-9A-Za-z])"
# Matches `mj:1112345678999p` or `mj:11p888s (640m<)` — a single-backtick code span prefixed
# with mj: for whole hands, melds included. The lookbehind/lookahead require a lone backtick on
# each side, so doubling the backticks (``mj:...``) escapes it and renders a literal code span.
INLINE_CODE_TILE_PATTERN: Final[str] = (
    rf"(?<!`)`mj:((?:(?:[0-9X]+[mpsz]|{MahjongParser.MELD_PATTERN.pattern})[ _|]*)+)`(?!`)"
)


class MahjongInlineProcessor(InlineProcessor):
    """Renders inline tile notation like :1m:, :123m456p:, `mj:123m`, or `mj:(123m<)` as SVG tiles."""

    def __init__(self, pattern: str, md: Markdown, config: dict, sprite: TileSprite | None = None) -> None:
        super().__init__(pattern, md)
        self.sprite = sprite
        self.parser = MahjongParser()
        self.renderer = MahjongRenderer(
            theme=config.get("theme", "auto"),
            closed_kan_style=config.get("closed_kan_style", "outer"),
            css_class="mahjong-inline",
            tile_back_color=config.get("tile_back_color"),
        )

    def handleMatch(self, m: re.Match, data: str) -> tuple[str | None, int | None, int | None]:
        notation = m.group(1)

        try:
            if self.parser.MELD_PATTERN.search(notation):
                hand = self.parser.parse(notation)
                tiles, melds = hand.closed_tiles, hand.melds
            else:
                # Plain tiles needn't be a legal hand, e.g. a row of five 1m.
                tiles, melds = self.parser.parse_tiles(notation), []
        except ParseError:
            return None, None, None

        html = self.renderer.render_tiles(tiles, sprite=self.sprite, melds=melds)
        placeholder = self.md.htmlStash.store(html)

        return placeholder, m.start(0), m.end(0)
