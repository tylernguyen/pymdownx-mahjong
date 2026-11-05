"""Superfences integration for pymdownx-mahjong.

Provides custom fence formatter and validator for use with pymdownx.superfences.
"""

from __future__ import annotations

from html import escape
from typing import Any

from .extension import MahjongExtension
from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer
from .utils import parse_hand_block


class _SuperfencesState:
    """Fallback state for the superfences formatter when the extension isn't registered."""

    def __init__(self) -> None:
        self.parser = MahjongParser()
        self._renderer: MahjongRenderer | None = None
        self._config: dict[str, Any] = {}

    def configure(self, **kwargs: Any) -> None:
        # Build the renderer before keeping the new config, so invalid config is rejected
        # here and leaves the previous config in place.
        config = {**self._config, **kwargs}
        renderer = self._build(config)
        self._config, self._renderer = config, renderer

    @property
    def renderer(self) -> MahjongRenderer:
        if self._renderer is None:
            self._renderer = self._build(self._config)
        return self._renderer

    @staticmethod
    def _build(config: dict[str, Any]) -> MahjongRenderer:
        return MahjongRenderer(
            theme=config.get("theme", "auto"),
            closed_kan_style=config.get("closed_kan_style", "outer"),
            tile_back_color=config.get("tile_back_color"),
            table_color=config.get("table_color"),
        )


_state = _SuperfencesState()


def configure_superfences(**kwargs: Any) -> None:
    """Configure the superfences integration when used without the extension.

    When the pymdownx_mahjong extension is registered, its own config is used instead.

    Example:
        from pymdownx_mahjong import configure_superfences
        configure_superfences(theme='dark', closed_kan_style='inner', tile_back_color='#2e7d6b')
    """
    _state.configure(**kwargs)


def superfences_validator(
    language: str,
    inputs: dict[str, str],
    options: dict[str, Any],
    attrs: dict[str, Any],
    md: Any,
) -> bool:
    """Validator for superfences custom fence."""
    return language == "mahjong"


def superfences_formatter(
    source: str,
    language: str,
    class_name: str,
    options: dict[str, Any],
    md: Any,
    **kwargs: Any,
) -> str:
    """Formatter for superfences custom fence."""
    parser = _state.parser
    ext = _find_extension(md)
    renderer = ext.renderer if ext else _state.renderer

    try:
        # Unstripped: a discards option's continuation lines are judged by indentation.
        hand, block_options, notation = parse_hand_block(source, parser)
    except ParseError as e:
        return _error_block(str(e))

    return renderer.render(
        hand,
        title=block_options.get("title"),
        notation=notation,
        # Without the extension's page-wide sprite, each block embeds the symbols it uses.
        sprite=ext.sprite if ext else None,
    )


def _find_extension(md: Any) -> MahjongExtension | None:
    """Return the MahjongExtension registered on ``md``, if any."""
    for ext in getattr(md, "registeredExtensions", ()):
        if isinstance(ext, MahjongExtension):
            return ext
    return None


def _error_block(message: str) -> str:
    return f'<div class="mahjong-error"><strong>Mahjong Error:</strong> {escape(message)}</div>'
