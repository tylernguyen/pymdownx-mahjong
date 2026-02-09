"""PyMdown Mahjong - Python Markdown extension to render and stylize Mahjong tiles"""

from .extension import MahjongExtension, makeExtension
from .inline import INLINE_TILE_PATTERN, MahjongInlineProcessor
from .parser import Hand, MahjongParser, Meld, Tile
from .renderer import MahjongRenderer
from .superfences import configure_superfences, superfences_formatter, superfences_validator

__all__ = [
    "MahjongExtension",
    "makeExtension",
    "MahjongParser",
    "MahjongRenderer",
    "MahjongInlineProcessor",
    "INLINE_TILE_PATTERN",
    "Tile",
    "Meld",
    "Hand",
    "superfences_formatter",
    "superfences_validator",
    "configure_superfences",
]

__version__ = "0.1.0"
