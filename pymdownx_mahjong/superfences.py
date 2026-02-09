"""Superfences integration for pymdownx-mahjong.

Provides custom fence formatter and validator for use with pymdownx.superfences.
"""

from __future__ import annotations

from html import escape
from typing import Any

from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer
from .utils import parse_hand_block


class _SuperfencesState:
    """Global state for superfences integration with lazy renderer creation."""

    def __init__(self) -> None:
        self.parser = MahjongParser()
        self._renderer: MahjongRenderer | None = None
        self._config: dict[str, Any] = {}

    def configure(self, **kwargs: Any) -> None:
        self._config.update(kwargs)
        self._renderer = None

    @property
    def renderer(self) -> MahjongRenderer:
        if self._renderer is None:
            self._renderer = MahjongRenderer(
                theme=self._config.get("theme", "auto"),
                closed_kan_style=self._config.get("closed_kan_style", "outer"),
            )
        return self._renderer


_state = _SuperfencesState()


def configure_superfences(**kwargs: Any) -> None:
    """Configure the superfences integration.

    Example:
        from pymdownx_mahjong import configure_superfences
        configure_superfences(closed_kan_style='outer')
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
    # Sync config from the markdown instance's registered extension
    if hasattr(md, 'registeredExtensions'):
        for ext in md.registeredExtensions:
            if hasattr(ext, 'config') and 'closed_kan_style' in ext.config:
                config = {key: ext.getConfig(key) for key in ext.config}
                _state.configure(**config)
                break

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
    renderer = _state.renderer

    content = source.strip()

    try:
        hand, block_options, notation = parse_hand_block(content, parser)
    except ParseError as e:
        return _error_block(str(e))

    return renderer.render(
        hand,
        title=block_options.get("title"),
        notation=notation,
    )


def _error_block(message: str) -> str:
    return f'<div class="mahjong-error"><strong>Mahjong Error:</strong> {escape(message)}</div>'
