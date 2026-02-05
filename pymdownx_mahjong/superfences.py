"""Superfences integration for pymdownx-mahjong.

Provides custom fence formatter and validator for use with pymdownx.superfences.
"""

from __future__ import annotations

from html import escape
from typing import Any

from .parser import MahjongParser, ParseError
from .renderer import MahjongRenderer
from .utils import apply_hand_options, parse_block_content


class _SuperfencesState:
    """Encapsulates global state for superfences integration.

    Uses lazy initialization to create parser/renderer on first use.
    Allows configuration via configure() method.
    """

    def __init__(self) -> None:
        self._renderer: MahjongRenderer | None = None
        self._parser: MahjongParser | None = None
        self._config: dict[str, Any] = {}

    def configure(self, **kwargs: Any) -> None:
        """Configure the superfences state.

        Args:
            **kwargs: Configuration options (theme, closed_kan_style, etc.)
        """
        self._config.update(kwargs)
        # Reset renderer to apply new config
        self._renderer = None

    @property
    def renderer(self) -> MahjongRenderer:
        """Get or create the renderer instance."""
        if self._renderer is None:
            self._renderer = MahjongRenderer(
                theme=self._config.get("theme", "auto"),
                inline_svg=self._config.get("inline_svg", True),
                closed_kan_style=self._config.get("closed_kan_style", "outer"),
            )
        return self._renderer

    @property
    def parser(self) -> MahjongParser:
        """Get or create the parser instance."""
        if self._parser is None:
            self._parser = MahjongParser()
        return self._parser


# Single state instance
_state = _SuperfencesState()


def configure_superfences(**kwargs: Any) -> None:
    """Configure the superfences integration.

    Call this before using superfences to set options like closed_kan_style.

    Example:
        from pymdownx_mahjong import configure_superfences
        configure_superfences(closed_kan_style='outer')

    Args:
        **kwargs: Configuration options
            - theme: 'light', 'dark', or 'auto'
            - closed_kan_style: 'outer' or 'inner'
            - inline_svg: bool
    """
    _state.configure(**kwargs)


def superfences_validator(
    language: str,
    inputs: dict[str, str],
    options: dict[str, Any],
    attrs: dict[str, Any],
    md: Any,
) -> bool:
    """Validator for superfences custom fence.

    Args:
        language: The language specified (should be 'mahjong')
        inputs: Input attributes from the fence
        options: Options dict to populate
        attrs: Attributes dict
        md: Markdown instance

    Returns:
        True if this is a valid mahjong fence
    """
    # Try to get config from the markdown instance's extension
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
    """Formatter for superfences custom fence.

    Args:
        source: The content inside the fence
        language: The language specified
        class_name: CSS class name
        options: Options from the fence
        md: Markdown instance
        **kwargs: Additional arguments

    Returns:
        Rendered HTML string
    """
    parser = _state.parser
    renderer = _state.renderer

    # Parse the content
    content = source.strip()
    notation, block_options = parse_block_content(content)

    if not notation:
        return _error_block("No hand notation provided")

    try:
        hand = parser.parse(notation)
    except ParseError as e:
        return _error_block(str(e))

    apply_hand_options(hand, parser, block_options)

    # Render the hand
    return renderer.render(
        hand,
        title=block_options.get("title"),
        notation=notation,
    )


def _error_block(message: str) -> str:
    """Generate an error block.

    Args:
        message: Error message

    Returns:
        HTML error block
    """
    return f'<div class="mahjong-error"><strong>Mahjong Error:</strong> {escape(message)}</div>'
