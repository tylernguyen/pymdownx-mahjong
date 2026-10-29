"""Python Markdown extension to render and stylize Mahjong tiles."""

from __future__ import annotations

import xml.etree.ElementTree as etree
from typing import TYPE_CHECKING, Any

import markdown
from markdown.treeprocessors import Treeprocessor

from .inline import INLINE_CODE_TILE_PATTERN, INLINE_TILE_PATTERN, MahjongInlineProcessor
from .renderer import MahjongRenderer
from .sprite import SPRITE_CLASS, SPRITE_STYLE, TileSprite

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
        # Collects the tile symbols used while converting a page; see MahjongSpriteTreeprocessor.
        self.sprite = TileSprite()

    def extendMarkdown(self, md: Markdown) -> None:
        config = {key: self.getConfig(key) for key in self.config}

        # The superfences formatter finds this extension on md and renders with this
        # renderer, so each Markdown instance keeps its own theme/closed_kan_style.
        # Constructing it here also rejects invalid config when the extension loads.
        self.renderer = MahjongRenderer(theme=config["theme"], closed_kan_style=config["closed_kan_style"])

        if str(config.get("enable_inline", "true")).lower() in ("true", "1", "yes"):
            # Priority 76: before pymdownx.emoji (75)
            inline_processor = MahjongInlineProcessor(INLINE_TILE_PATTERN, md, config, self.sprite)
            md.inlinePatterns.register(inline_processor, "mahjong_inline", 76)

            # Priority 195: before the built-in backtick code span processor (190)
            code_processor = MahjongInlineProcessor(INLINE_CODE_TILE_PATTERN, md, config, self.sprite)
            md.inlinePatterns.register(code_processor, "mahjong_inline_code", 195)

        # Priority -10: after every processor that renders tiles, and after MkDocs reads the
        # page title from the first element (1), since the sprite becomes the first element.
        md.treeprocessors.register(MahjongSpriteTreeprocessor(md, self.sprite), "mahjong_sprite", -10)

        md.registerExtension(self)

    def reset(self) -> None:
        self.sprite.reset()


class MahjongSpriteTreeprocessor(Treeprocessor):
    """Emits each tile symbol used on the page once, as the first element of the page.

    A treeprocessor rather than a postprocessor: the toc extension runs postprocessors on
    its own fragment first, which would consume the sprite. Placed first rather than last
    so truncated output (e.g. blog excerpts) keeps it.
    """

    def __init__(self, md: Markdown, sprite: TileSprite) -> None:
        super().__init__(md)
        self.sprite = sprite

    def run(self, root: etree.Element) -> None:
        symbols = self.sprite.render_symbols()
        self.sprite.reset()
        if not symbols:
            return
        container = etree.Element("div", {"class": SPRITE_CLASS, "aria-hidden": "true", "style": SPRITE_STYLE})
        container.text = self.md.htmlStash.store(symbols)
        container.tail = "\n"
        root.insert(0, container)


def makeExtension(**kwargs: Any) -> MahjongExtension:
    """Entry point called by Python Markdown."""
    return MahjongExtension(**kwargs)
