"""Tests for the Markdown extension."""

import markdown


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

    def test_plain_code_span_is_not_rendered(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("Plain `123m` code")
        assert "<code>123m</code>" in out
        assert "mahjong-inline" not in out

    def test_extension_registered_for_superfences(self):
        from pymdownx_mahjong import MahjongExtension

        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert any(isinstance(ext, MahjongExtension) for ext in md.registeredExtensions)


class TestMakeExtension:
    def test_make_extension_with_config(self):
        from pymdownx_mahjong import makeExtension

        ext = makeExtension(theme="dark", enable_inline="false", closed_kan_style="inner")
        assert ext.getConfig("theme") == "dark"
        assert ext.getConfig("enable_inline") == "false"
        assert ext.getConfig("closed_kan_style") == "inner"


class TestConfigPropagation:
    """Extension config must flow through to the superfences renderer."""

    def test_theme_propagates_to_superfences_state(self):
        from pymdownx_mahjong.superfences import _state

        markdown.Markdown(
            extensions=["pymdownx_mahjong"],
            extension_configs={"pymdownx_mahjong": {"theme": "dark"}},
        )
        assert _state._config.get("theme") == "dark"

    def test_closed_kan_style_propagates_to_superfences_state(self):
        from pymdownx_mahjong.superfences import _state

        markdown.Markdown(
            extensions=["pymdownx_mahjong"],
            extension_configs={"pymdownx_mahjong": {"closed_kan_style": "inner"}},
        )
        assert _state._config.get("closed_kan_style") == "inner"

    def test_renderer_uses_propagated_config(self):
        from pymdownx_mahjong.superfences import _state

        markdown.Markdown(
            extensions=["pymdownx_mahjong"],
            extension_configs={"pymdownx_mahjong": {"theme": "dark", "closed_kan_style": "inner"}},
        )
        renderer = _state.renderer
        assert renderer.theme == "dark"
        assert renderer.closed_kan_style == "inner"
