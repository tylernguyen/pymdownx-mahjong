"""Tests for the Markdown extension."""

import markdown
import pytest


class TestMahjongExtension:
    def test_block_processor_not_registered(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert "mahjong" not in md.parser.blockprocessors

    def test_inline_processor_registered_by_default(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert "mahjong_inline" in md.inlinePatterns

    def test_inline_code_processor_registered_by_default(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert "mahjong_inline_code" in md.inlinePatterns

    def test_inline_processor_disabled(self):
        md = markdown.Markdown(
            extensions=["pymdownx_mahjong"],
            extension_configs={"pymdownx_mahjong": {"enable_inline": "false"}},
        )
        assert "mahjong_inline" not in md.inlinePatterns
        assert "mahjong_inline_code" not in md.inlinePatterns

    def test_inline_code_renders_hand_as_tiles(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("A hand `mj:1112345678999p` here")
        assert "mahjong-inline" in out
        assert "<code" not in out

    def test_inline_face_down_tile(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("a :Xz: b")
        assert out.count("mahjong-tile-back") == 1
        assert "mahjong-inline" in out

    def test_inline_face_down_mixed_with_tiles(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert(":1mXz3m:")
        assert out.count("mahjong-tile-back") == 1
        assert out.count('data-tile="1m"') == 1
        assert out.count('data-tile="3m"') == 1

    def test_double_backtick_escapes_mj_code(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("``mj:123456789m``")
        assert "mahjong-inline" not in out
        assert "<code>mj:123456789m</code>" in out

    def test_plain_code_span_is_not_rendered(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("Plain `123m` code")
        assert "<code>123m</code>" in out
        assert "mahjong-inline" not in out

    def test_extension_registered_for_superfences(self):
        from pymdownx_mahjong import MahjongExtension

        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert any(isinstance(ext, MahjongExtension) for ext in md.registeredExtensions)


class TestPageSprite:
    def _md(self):
        from pymdownx_mahjong import superfences_formatter

        config = {"custom_fences": [{"name": "mahjong", "class": "mahjong", "format": superfences_formatter}]}
        return markdown.Markdown(
            extensions=["pymdownx_mahjong", "pymdownx.superfences"],
            extension_configs={"pymdownx_mahjong": {"theme": "light"}, "pymdownx.superfences": config},
        )

    def test_symbols_emitted_once_per_page(self):
        md = self._md()
        out = md.convert(":1m: and :1m2m:\n\n```mahjong\n111m\n```\n\n```mahjong\n1m\n```")

        assert out.count('<symbol id="mj-light-1m"') == 1
        assert out.count('<symbol id="mj-light-2m"') == 1
        assert out.count('class="mahjong-sprite"') == 1
        assert out.startswith('<div aria-hidden="true" class="mahjong-sprite"')

    def test_sprite_survives_toc(self):
        """toc runs postprocessors on its own fragment; the sprite must stay in the page."""
        md = markdown.Markdown(extensions=["toc", "pymdownx_mahjong"])
        out = md.convert("# Title :1m:\n\n:2p:")

        assert '<symbol id="mj-light-1m"' in out
        assert '<symbol id="mj-light-2p"' in out
        assert "mahjong-sprite" not in md.toc

    def test_sprite_does_not_hide_first_heading(self):
        """MkDocs takes the page title from the first element, which must stay the h1."""
        from markdown.treeprocessors import Treeprocessor

        seen = []

        class FirstTag(Treeprocessor):
            def run(self, root):
                seen.append(root[0].tag)

        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        md.treeprocessors.register(FirstTag(md), "first_tag", 1)
        md.convert("# Title\n\n:1m:")

        assert seen == ["h1"]

    def test_sprite_resets_between_pages(self):
        md = self._md()
        md.convert(":1m:")
        out = md.reset().convert(":2p:")

        assert "mj-light-1m" not in out
        assert '<symbol id="mj-light-2p"' in out

    def test_no_sprite_without_tiles(self):
        md = self._md()
        assert "mahjong-sprite" not in md.convert("plain text")


class TestMakeExtension:
    def test_make_extension_with_config(self):
        from pymdownx_mahjong import makeExtension

        ext = makeExtension(theme="dark", enable_inline="false", closed_kan_style="inner")
        assert ext.getConfig("theme") == "dark"
        assert ext.getConfig("enable_inline") == "false"
        assert ext.getConfig("closed_kan_style") == "inner"


class TestConfigPropagation:
    """Extension config must flow through to the superfences renderer of the same Markdown instance."""

    @staticmethod
    def _md(**config):
        from pymdownx_mahjong import superfences_formatter, superfences_validator

        fences = [
            {
                "name": "mahjong",
                "class": "mahjong",
                "format": superfences_formatter,
                "validator": superfences_validator,
            }
        ]
        return markdown.Markdown(
            extensions=["pymdownx_mahjong", "pymdownx.superfences"],
            extension_configs={"pymdownx_mahjong": config, "pymdownx.superfences": {"custom_fences": fences}},
        )

    def test_fence_uses_extension_config(self):
        out = self._md(theme="dark", closed_kan_style="inner").convert("```mahjong\n[1111z]\n```")
        assert "mahjong-theme-dark" in out
        # inner: front, back, back, front
        assert out.count("mahjong-tile-back") == 2

    def test_config_does_not_leak_between_instances(self):
        dark = self._md(theme="dark")
        self._md(theme="light")
        out = dark.convert("```mahjong\n123m\n```")
        assert "mahjong-theme-dark" in out
        assert "mahjong-theme-light" not in out


class TestConfigValidation:
    def test_invalid_theme_rejected(self):
        with pytest.raises(ValueError, match="theme"):
            markdown.Markdown(
                extensions=["pymdownx_mahjong"],
                extension_configs={"pymdownx_mahjong": {"theme": "Dark"}},
            )

    def test_invalid_closed_kan_style_rejected(self):
        with pytest.raises(ValueError, match="closed_kan_style"):
            markdown.Markdown(
                extensions=["pymdownx_mahjong"],
                extension_configs={"pymdownx_mahjong": {"closed_kan_style": "inside"}},
            )
