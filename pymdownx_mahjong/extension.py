"""Python Markdown extension to render and stylize Mahjong tiles."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import markdown

from .inline import INLINE_CODE_TILE_PATTERN, INLINE_TILE_PATTERN, MahjongInlineProcessor

if TYPE_CHECKING:
    from markdown import Markdown


class MahjongExtension(markdown.Extension):
    def __init__(self, **kwargs: Any) -> None:
        self.config = {
            "theme": ["auto", "Color theme: 'light', 'dark', or 'auto'"],
            "enable_inline": ["true", "Enable inline tile syntax (:1m:)"],
            "closed_kan_style": ["outer", "Closed kan style: 'outer' or 'inner'"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        config = {key: self.getConfig(key) for key in self.config}

        # Push config to superfences state eagerly so the formatter always has
        # the correct theme/closed_kan_style even when md is unavailable there.
        from .superfences import _state  # lazy import avoids circular dependency
        _state.configure(**config)

        if str(config.get("enable_inline", "true")).lower() in ("true", "1", "yes"):
            # Priority 76: before pymdownx.emoji (75)
            inline_processor = MahjongInlineProcessor(INLINE_TILE_PATTERN, md, config)
            md.inlinePatterns.register(inline_processor, "mahjong_inline", 76)

            # Priority 195: before the built-in backtick code span processor (190)
            code_processor = MahjongInlineProcessor(INLINE_CODE_TILE_PATTERN, md, config)
            md.inlinePatterns.register(code_processor, "mahjong_inline_code", 195)

        md.registerExtension(self)


def makeExtension(**kwargs: Any) -> MahjongExtension:
    """Entry point called by Python Markdown."""
    return MahjongExtension(**kwargs)
