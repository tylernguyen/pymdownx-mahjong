"""Inline processor for Mahjong tile notation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from markdown.inlinepatterns import InlineProcessor

from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer

if TYPE_CHECKING:
    import re

    from markdown import Markdown

# Matches :123m:, :1z:, :Xz:, :1234567Xz: etc. — rank+suit groups where a rank is a
# digit or X (X = a face-down tile, e.g. Xz).
INLINE_TILE_PATTERN: Final[str] = r":((?:[0-9X]+[mpsz])+):"
# Matches `mj:1112345678999p` — a single-backtick code span prefixed with mj: for whole
# hands. The lookbehind/lookahead require a lone backtick on each side, so doubling the
# backticks (``mj:...``) escapes it and renders a literal code span instead.
INLINE_CODE_TILE_PATTERN: Final[str] = r"(?<!`)`mj:((?:[0-9X]+[mpsz])+)`(?!`)"


class MahjongInlineProcessor(InlineProcessor):
    """Renders inline tile notation like :1m:, :123m456p:, or `mj:123m` as SVG tiles."""

    def __init__(self, pattern: str, md: Markdown, config: dict) -> None:
        super().__init__(pattern, md)
        self.parser = MahjongParser()
        self.renderer = MahjongRenderer(
            theme=config.get("theme", "auto"),
            css_class="mahjong-inline",
        )

    def handleMatch(self, m: re.Match, data: str) -> tuple[str | None, int | None, int | None]:
        notation = m.group(1)

        try:
            tiles = self.parser.parse_tiles(notation)
        except ParseError:
            return None, None, None

        html = self.renderer.render_tiles(tiles)
        placeholder = self.md.htmlStash.store(html)

        return placeholder, m.start(0), m.end(0)
