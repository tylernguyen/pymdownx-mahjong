"""Inline processor for Mahjong tile notation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from markdown.inlinepatterns import InlineProcessor

from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer

if TYPE_CHECKING:
    import re

    from markdown import Markdown

# Matches :123m:, :1z:, :0m: etc. — one or more digit groups followed by m/p/s/z
INLINE_TILE_PATTERN: Final[str] = r":([0-9]+[mpsz])+:"


class MahjongInlineProcessor(InlineProcessor):
    """Renders inline tile notation like :1m:, :123m456p: as SVG tiles."""

    def __init__(self, pattern: str, md: Markdown, config: dict) -> None:
        super().__init__(pattern, md)
        self.parser = MahjongParser()
        self.renderer = MahjongRenderer(
            theme=config.get("theme", "auto"),
            css_class="mahjong-inline",
        )

    def handleMatch(self, m: re.Match, data: str) -> tuple[str | None, int | None, int | None]:
        full_match = m.group(0)
        notation = full_match[1:-1]  # Strip colons

        try:
            tiles = self.parser.parse_tiles(notation)
        except ParseError:
            return None, None, None

        if not tiles:
            return None, None, None

        html = self.renderer.render_tiles(tiles)
        placeholder = self.md.htmlStash.store(html)

        return placeholder, m.start(0), m.end(0)
