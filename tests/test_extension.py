"""Tests for the Markdown extension."""

import markdown


class TestMahjongExtension:
    def test_extension_loads(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert "mahjong" in md.parser.blockprocessors

    def test_simple_block_conversion(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        result = md.convert("```mahjong\n123m456p789s11222z\n```")

        assert "mahjong-hand" in result
        assert 'data-tile="1m"' in result
        assert "<svg" in result or "svg" in result.lower()

    def test_extended_block_syntax(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        result = md.convert("```mahjong\nhand: 123m456p789s11222z\ntitle: Test Hand\n```")

        assert "mahjong-caption" in result
        assert "Test Hand" in result

    def test_draw_tile_syntax(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        result = md.convert("```mahjong\nhand: 123m456p789s1112z\ndraw: 2z\n```")

        assert "mahjong-hand-draw" in result
        assert 'data-tile="2z"' in result

    def test_error_handling(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        result = md.convert("```mahjong\ninvalid notation 8z9z\n```")

        assert "mahjong-error" in result

    def test_empty_block(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        result = md.convert("```mahjong\n```")

        assert "mahjong-error" in result
        assert "No hand notation" in result

    def test_unclosed_block(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        result = md.convert("```mahjong\n123m456p789s")

        assert "mahjong-error" in result
        assert "Unclosed mahjong fence" in result

    def test_multiple_blocks(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        source = "```mahjong\n123m456p789s11222z\n```\n\nSome text.\n\n```mahjong\n111m222p333s44455z\n```"
        result = md.convert(source)

        assert result.count('class="mahjong-hand"') == 2

    def test_preserves_other_content(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        source = "# Heading\n\nSome **bold** text.\n\n```mahjong\n123m456p789s11222z\n```\n\nMore content."
        result = md.convert(source)

        assert "<h1>" in result
        assert "<strong>bold</strong>" in result
        assert "mahjong-hand" in result
        assert "More content" in result

    def test_partial_hands_allowed(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        result = md.convert("```mahjong\n123m\n```")

        assert "mahjong-hand" in result
        assert "mahjong-error" not in result

    def test_invalid_option_reports_error(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        result = md.convert("```mahjong\nhand: 123m456p789s11222z\ndora: 8z\n```")

        assert "mahjong-error" in result


class TestMakeExtension:
    def test_make_extension_with_config(self):
        from pymdownx_mahjong import makeExtension

        ext = makeExtension(theme="dark", closed_kan_style="inner")
        assert ext.getConfig("theme") == "dark"
        assert ext.getConfig("closed_kan_style") == "inner"
