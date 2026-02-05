"""Python Markdown extension to render and stylize Mahjong tiles."""

from __future__ import annotations

import re
import xml.etree.ElementTree as etree
from typing import TYPE_CHECKING, Any

import markdown
from markdown.blockprocessors import BlockProcessor

from .inline import INLINE_TILE_PATTERN, MahjongInlineProcessor
from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer
from .utils import _to_bool, apply_hand_options, parse_block_content

if TYPE_CHECKING:
    from markdown import Markdown
    from markdown.blockparser import BlockParser


class MahjongBlockProcessor(BlockProcessor):
    """Block processor that handles ```mahjong fenced code blocks.

    Converts mahjong notation blocks into HTML.
    """

    # Pattern to match the start of a mahjong block
    START_PATTERN = re.compile(r"^`{3,}mahjong\s*$")
    END_PATTERN = re.compile(r"^`{3,}\s*$")

    md: Markdown

    def __init__(self, parser: BlockParser, config: dict[str, Any]) -> None:
        """Initialize the block processor.

        Args:
            parser: Block parser instance
            config: Extension configuration
        """
        super().__init__(parser)
        self.config = config
        self.mj_parser = MahjongParser()
        self.renderer = MahjongRenderer(
            theme=config.get("theme", "light"),

            closed_kan_style=config.get("closed_kan_style", "outer"),
        )

    def test(self, parent: etree.Element, block: str) -> bool:
        """Test if this block should be processed.

        Args:
            parent: Parent element
            block: Block text

        Returns:
            True if block starts with ```mahjong
        """
        return bool(self.START_PATTERN.match(block.split("\n")[0]))

    def run(self, parent: etree.Element, blocks: list[str]) -> bool:
        """Process the mahjong block.

        Args:
            parent: Parent element
            blocks: List of blocks

        Returns:
            True if block was processed
        """
        block = blocks.pop(0)
        lines = block.split("\n")

        # Find the end of the fenced block
        content_lines: list[str] = []
        fence_closed = False

        # Skip the opening fence
        for i, line in enumerate(lines[1:], 1):
            if self.END_PATTERN.match(line):
                fence_closed = True
                # Put remaining lines back
                remaining = "\n".join(lines[i + 1 :])
                if remaining.strip():
                    blocks.insert(0, remaining)
                break
            content_lines.append(line)

        # If fence wasn't closed in this block, check subsequent blocks
        if not fence_closed:
            while blocks:
                next_block = blocks.pop(0)
                next_lines = next_block.split("\n")
                for i, line in enumerate(next_lines):
                    if self.END_PATTERN.match(line):
                        fence_closed = True
                        remaining = "\n".join(next_lines[i + 1 :])
                        if remaining.strip():
                            blocks.insert(0, remaining)
                        break
                    content_lines.append(line)
                if fence_closed:
                    break

        content = "\n".join(content_lines).strip()

        # Parse block content
        notation, options = parse_block_content(content)

        if not notation:
            self._render_error(parent, "No hand notation provided")
            return True

        try:
            hand = self.mj_parser.parse(notation)
        except ParseError as e:
            self._render_error(parent, str(e))
            return True

        apply_hand_options(hand, self.mj_parser, options)

        # Render the hand
        html = self.renderer.render(
            hand,
            title=options.get("title"),
            notation=notation,
        )

        # Store the raw HTML and use a placeholder that survives processing
        placeholder = self.md.htmlStash.store(html)
        p = etree.SubElement(parent, "div")
        p.text = placeholder

        return True

    def _render_error(self, parent: etree.Element, message: str) -> None:
        """Render an error message.

        Args:
            parent: Parent element
            message: Error message
        """
        div = etree.SubElement(parent, "div")
        div.set("class", "mahjong-error")
        strong = etree.SubElement(div, "strong")
        strong.text = "Mahjong Error: "
        strong.tail = message


class MahjongExtension(markdown.Extension):
    def __init__(self, **kwargs: Any) -> None:
        """Initialize the extension with configuration.

        Args:
            **kwargs: Configuration options
        """
        # Define configuration options with defaults
        # Note: Use strings for boolean defaults for YAML compatibility
        self.config = {
            "theme": ["auto", "Color theme: 'light', 'dark', or 'auto'"],

            "enable_inline": ["true", "Enable inline tile syntax (:1m:)"],
            "closed_kan_style": ["outer", "Closed kan style: 'outer' or 'inner'"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the extension with the Markdown instance.

        Args:
            md: Markdown instance
        """
        # Get configuration values
        config = {key: self.getConfig(key) for key in self.config}

        # Register block processor at high priority (before fenced_code)
        processor = MahjongBlockProcessor(md.parser, config)
        processor.md = md
        md.parser.blockprocessors.register(processor, "mahjong", 110)

        # Register inline processor if enabled
        # Priority 76 to run before pymdownx.emoji (which uses 75)
        if _to_bool(config.get("enable_inline", True)):
            inline_processor = MahjongInlineProcessor(INLINE_TILE_PATTERN, md, config)
            md.inlinePatterns.register(inline_processor, "mahjong_inline", 76)

        # Reset on each conversion
        md.registerExtension(self)


def makeExtension(**kwargs: Any) -> MahjongExtension:
    """Create the extension instance.

    This is the entry point called by Python Markdown.

    Args:
        **kwargs: Configuration options

    Returns:
        MahjongExtension instance
    """
    return MahjongExtension(**kwargs)
