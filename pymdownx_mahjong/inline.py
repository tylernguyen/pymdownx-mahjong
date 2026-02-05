"""Inline processor for Mahjong tile notation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from markdown.inlinepatterns import InlineProcessor

from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer

if TYPE_CHECKING:
    import re

    from markdown import Markdown

# Pattern matches :123m:, :1z:, :0m: (red dora), etc.
# Must be valid MPSZ: one or more groups of digits followed by m/p/s/z
# Examples: :1m:, :123p:, :5z:, :0s:, :123m456p:
INLINE_TILE_PATTERN: Final[str] = r":([0-9]+[mpsz])+:"


def _to_bool(value: Any) -> bool:
    """Convert a value to boolean, handling string 'true'/'false'."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


class MahjongInlineProcessor(InlineProcessor):
    """Inline processor for mahjong tile notation.

    Matches patterns like :1m:, :123m:, :123m456p:
    Renders emoji-sized tiles inline with text.
    """

    def __init__(self, pattern: str, md: Markdown, config: dict[str, Any]) -> None:
        """Initialize the inline processor.

        Args:
            pattern: Regex pattern to match
            md: Markdown instance
            config: Extension configuration
        """
        super().__init__(pattern, md)
        self.config = config
        self.parser = MahjongParser()
        self.renderer = MahjongRenderer(
            theme=config.get("theme", "auto"),
            inline_svg=_to_bool(config.get("inline_svg", True)),
            assets_path=config.get("assets_path"),
            css_class="mahjong-inline",
        )

    def handleMatch(self, m: re.Match, data: str) -> tuple[str | None, int | None, int | None]:
        """Handle matched inline tile notation.

        Args:
            m: Match object
            data: Full text being processed

        Returns:
            Tuple of (placeholder, start_index, end_index) or (None, None, None) if invalid
        """
        # Extract notation without colons
        full_match = m.group(0)
        notation = full_match[1:-1]  # Strip leading/trailing colons

        try:
            tiles = self.parser.parse_tiles(notation)
        except ParseError:
            # Invalid notation - return None to leave text unchanged
            return None, None, None

        if not tiles:
            return None, None, None

        # Render tiles as HTML
        html = self.renderer.render_tiles(tiles)

        # Store raw HTML and return placeholder
        placeholder = self.md.htmlStash.store(html)

        return placeholder, m.start(0), m.end(0)
