"""Tests for the Markdown extension."""

import markdown
import pytest


class TestMahjongExtension:
    """Tests for the MahjongExtension class."""

    def test_extension_loads(self):
        """Test that the extension loads correctly."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert "mahjong" in md.parser.blockprocessors

    def test_simple_block_conversion(self):
        """Test converting a simple mahjong block."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        # Valid 14-tile hand: 3+3+3+5 = 14 tiles
        source = """
```mahjong
123m456p789s11222z
```
"""
        result = md.convert(source)

        assert "mahjong-hand" in result
        assert "mahjong-tiles" in result
        assert 'data-tile="1m"' in result

    def test_extended_block_syntax(self):
        """Test extended block syntax with options."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        # Valid 14-tile hand with title
        source = """
```mahjong
hand: 123m456p789s11222z
title: Test Hand
```
"""
        result = md.convert(source)

        assert "mahjong-hand" in result
        assert "mahjong-caption" in result
        assert "Test Hand" in result

    def test_draw_tile_syntax(self):
        """Test draw: syntax for specifying the drawn tile."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        source = """
```mahjong
hand: 123m456p789s1112z
draw: 2z
title: Tsumo Hand
```
"""
        result = md.convert(source)

        assert "mahjong-hand" in result
        assert "mahjong-hand-draw" in result
        assert 'data-tile="2z"' in result

    def test_hand_without_draw_tile(self):
        """Test that hands without draw: don't have a draw section."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        source = """
```mahjong
123m456p789s11222z
```
"""
        result = md.convert(source)

        assert "mahjong-hand" in result
        # Should NOT have a draw section since draw: was not specified
        assert "mahjong-hand-draw" not in result

    def test_error_handling(self):
        """Test that invalid notation produces error message."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        source = """
```mahjong
invalid notation 8z9z
```
"""
        result = md.convert(source)

        assert "mahjong-error" in result

    def test_empty_block(self):
        """Test handling of empty mahjong block."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        source = """
```mahjong
```
"""
        result = md.convert(source)

        assert "mahjong-error" in result
        assert "No hand notation" in result

    def test_configuration_options(self):
        """Test that configuration options are respected."""
        md = markdown.Markdown(
            extensions=["pymdownx_mahjong"],
            extension_configs={
                "pymdownx_mahjong": {
                    "theme": "dark",
                }
            },
        )

        # Valid 14-tile hand
        source = """
```mahjong
123m456p789s11222z
```
"""
        result = md.convert(source)

        assert "mahjong-hand" in result

    def test_multiple_blocks(self):
        """Test converting multiple mahjong blocks."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        # Two valid 14-tile hands
        source = """
```mahjong
123m456p789s11222z
```

Some text between.

```mahjong
111m222p333s44455z
```
"""
        result = md.convert(source)

        # Count figure elements with class mahjong-hand (more specific than just class name)
        assert result.count('class="mahjong-hand"') == 2
        assert 'data-tile="1m"' in result
        assert 'data-tile="4z"' in result

    def test_inline_svg_default(self):
        """Test that SVG is inlined by default."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        # Valid 14-tile hand
        source = """
```mahjong
123m456p789s11222z
```
"""
        result = md.convert(source)

        # Should contain SVG element, not img
        assert "<svg" in result or "svg" in result.lower()

    def test_preserves_other_content(self):
        """Test that other markdown content is preserved."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        # Valid 14-tile hand
        source = """
# Heading

Some **bold** text.

```mahjong
123m456p789s11222z
```

More content.
"""
        result = md.convert(source)

        assert "<h1>" in result
        assert "<strong>bold</strong>" in result
        assert "mahjong-hand" in result
        assert "More content" in result

    def test_partial_hands_allowed(self):
        """Test that partial hands (fewer than 14 tiles) are allowed."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])

        # Partial hand - only 3 tiles
        source = """
```mahjong
123m
```
"""
        result = md.convert(source)

        assert "mahjong-hand" in result
        assert "mahjong-error" not in result


class TestMakeExtension:
    """Tests for the makeExtension entry point."""

    def test_make_extension(self):
        """Test that makeExtension works."""
        from pymdownx_mahjong import makeExtension

        ext = makeExtension()
        assert ext is not None

    def test_make_extension_with_config(self):
        """Test makeExtension with configuration."""
        from pymdownx_mahjong import makeExtension

        ext = makeExtension(theme="dark", closed_kan_style="inner")
        assert ext.getConfig("theme") == "dark"
        assert ext.getConfig("closed_kan_style") == "inner"
