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
from .utils import parse_hand_block

if TYPE_CHECKING:
    from markdown import Markdown
    from markdown.blockparser import BlockParser


class MahjongBlockProcessor(BlockProcessor):
    """Block processor that handles ```mahjong fenced code blocks."""

    START_PATTERN = re.compile(r"^`{3,}mahjong\s*$")
    END_PATTERN = re.compile(r"^`{3,}\s*$")

    md: Markdown

    def __init__(self, parser: BlockParser, config: dict[str, Any]) -> None:
        super().__init__(parser)
        self.config = config
        self.mj_parser = MahjongParser()
        self.renderer = MahjongRenderer(
            theme=config.get("theme", "auto"),
            closed_kan_style=config.get("closed_kan_style", "outer"),
        )

    def test(self, parent: etree.Element, block: str) -> bool:
        return bool(self.START_PATTERN.match(block.split("\n")[0]))

    def run(self, parent: etree.Element, blocks: list[str]) -> bool:
        block = blocks.pop(0)
        lines = block.split("\n")

        content_lines: list[str] = []
        fence_closed = False

        for i, line in enumerate(lines[1:], 1):
            if self.END_PATTERN.match(line):
                fence_closed = True
                remaining = "\n".join(lines[i + 1 :])
                if remaining.strip():
                    blocks.insert(0, remaining)
                break
            content_lines.append(line)

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

        if not fence_closed:
            self._render_error(parent, "Unclosed mahjong fence")
            return True

        content = "\n".join(content_lines).strip()

        try:
            hand, options, notation = parse_hand_block(content, self.mj_parser)
        except ParseError as e:
            self._render_error(parent, str(e))
            return True

        html = self.renderer.render(
            hand,
            title=options.get("title"),
            notation=notation,
        )

        # Store raw HTML as a placeholder that survives markdown processing
        placeholder = self.md.htmlStash.store(html)
        p = etree.SubElement(parent, "div")
        p.text = placeholder

        return True

    def _render_error(self, parent: etree.Element, message: str) -> None:
        div = etree.SubElement(parent, "div")
        div.set("class", "mahjong-error")
        strong = etree.SubElement(div, "strong")
        strong.text = "Mahjong Error: "
        strong.tail = message


class MahjongExtension(markdown.Extension):
    def __init__(self, **kwargs: Any) -> None:
        # String defaults for YAML compatibility
        self.config = {
            "theme": ["auto", "Color theme: 'light', 'dark', or 'auto'"],
            "enable_inline": ["true", "Enable inline tile syntax (:1m:)"],
            "closed_kan_style": ["outer", "Closed kan style: 'outer' or 'inner'"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        config = {key: self.getConfig(key) for key in self.config}

        # Priority 110: before fenced_code
        processor = MahjongBlockProcessor(md.parser, config)
        processor.md = md
        md.parser.blockprocessors.register(processor, "mahjong", 110)

        # Priority 76: before pymdownx.emoji (75)
        if str(config.get("enable_inline", "true")).lower() in ("true", "1", "yes"):
            inline_processor = MahjongInlineProcessor(INLINE_TILE_PATTERN, md, config)
            md.inlinePatterns.register(inline_processor, "mahjong_inline", 76)

        md.registerExtension(self)


def makeExtension(**kwargs: Any) -> MahjongExtension:
    """Entry point called by Python Markdown."""
    return MahjongExtension(**kwargs)
