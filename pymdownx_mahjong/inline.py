"""Inline processor for Mahjong tile notation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from markdown.inlinepatterns import InlineProcessor

from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer

if TYPE_CHECKING:
    from markdown import Markdown

    from .sprite import TileSprite

# Matches :123m:, :1z:, :Xz:, :1234567Xz: etc. — rank+suit groups where a rank is a
# digit or X (X = a face-down tile, e.g. Xz). An ASCII letter or digit on either side means
# it's ordinary text like 10:30m:15, not tiles; \w would also reject tiles beside CJK text.
INLINE_TILE_PATTERN: Final[str] = r"(?<![0-9A-Za-z]):((?:[0-9X]+[mpsz])+):(?![0-9A-Za-z])"
# Matches every code span, so `mj:` inside a longer span or after an escaped backtick isn't
# mistaken for one of ours; MahjongCodeSpanProcessor picks out ours. An even run of backslashes
# escapes only itself, so it may come first. Groups: 1 those backslashes, 2 the opening
# backticks, 3 the content. (Python Markdown's own BACKTICK_RE differs between versions.)
INLINE_CODE_PATTERN: Final[str] = r"(?<!\\)((?:\\{2})*)(`+)(.+?)(?<!`)\2(?!`)"
# The content of `mj:1112345678999p` or `mj:11p888s (640m<)` — for whole hands, melds included.
_MJ_CODE: Final[re.Pattern[str]] = re.compile(
    rf"mj:((?:(?:[0-9X]+[mpsz]|{MahjongParser.MELD_PATTERN.pattern})[ _|]*)+)"
)


class MahjongInlineProcessor(InlineProcessor):
    """Renders inline tile notation like :1m: or :123m456p: as SVG tiles."""

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
        return self._render(m.group(1), m.start(0), m.end(0))

    def _render(self, notation: str, start: int, end: int) -> tuple[str | None, int | None, int | None]:
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

        return placeholder, start, end


class MahjongCodeSpanProcessor(MahjongInlineProcessor):
    """Renders single-backtick `mj:123m` and `mj:(123m<)` code spans as SVG tiles, leaving every
    other code span for Python Markdown's own processor; so doubling the backticks (``mj:...``)
    escapes one and renders a literal code span."""

    def handleMatch(self, m: re.Match, data: str) -> tuple[str | None, int | None, int | None]:
        code = _MJ_CODE.fullmatch(m.group(3)) if m.group(2) == "`" else None
        # Starting at the backticks leaves any backslashes before them for the escape processor.
        return self._render(code.group(1), m.start(2), m.end(0)) if code else (None, None, None)
