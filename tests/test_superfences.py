"""Tests for the superfences integration."""

import pytest

from pymdownx_mahjong.superfences import (
    _error_block,
    _SuperfencesState,
    configure_superfences,
    superfences_formatter,
    superfences_validator,
)


@pytest.fixture(autouse=True)
def reset_superfences_state(monkeypatch):
    """Isolate each test from module-level _state side-effects."""
    import pymdownx_mahjong.superfences as sf

    monkeypatch.setattr(sf, "_state", _SuperfencesState())


def _format(source):
    return superfences_formatter(source=source, language="mahjong", class_name="", options={}, md=None)


class TestSuperfencesValidator:
    def test_validator_accepts_mahjong(self):
        result = superfences_validator(language="mahjong", inputs={}, options={}, attrs={}, md=None)
        assert result is True

    def test_validator_rejects_other_languages(self):
        for lang in ["python", "javascript", "", "MAHJONG"]:
            result = superfences_validator(language=lang, inputs={}, options={}, attrs={}, md=None)
            assert result is False, f"Should reject language: {lang}"


class TestSuperfencesFormatter:
    def test_formatter_renders_simple_hand(self):
        html = _format("123m456p789s11222z")

        assert "mahjong-hand" in html
        assert 'data-tile="1m"' in html

    def test_formatter_with_yaml_options(self):
        html = _format("hand: 123m\ntitle: Test Hand")

        assert "Test Hand" in html
        assert 'class="mahjong-caption"' in html

    def test_formatter_with_dora(self):
        html = _format("hand: 123m456p789s11222z\ndora: 5m")

        assert 'class="mahjong-dora"' in html

    def test_formatter_with_draw(self):
        html = _format("hand: 123m456p789s1112z\ndraw: 2z")

        assert 'class="mahjong-hand-draw"' in html

    def test_formatter_invalid_options(self):
        html = _format("hand: 123m456p789s11222z\ndora: 8z")

        assert "mahjong-error" in html

    def test_formatter_invalid_notation(self):
        html = _format("8z9z")

        assert "mahjong-error" in html

    def test_formatter_no_hand(self):
        for source in ("", "title: Only Title"):
            html = _format(source)
            assert "mahjong-error" in html
            assert "No hand notation" in html

    def test_honba_and_riichi(self):
        html = _format("123m\nriichi: 1\nhonba: 2")

        assert 'class="mahjong-sticks"' in html
        assert 'aria-label="Riichi sticks: 1"' in html
        assert 'aria-label="Honba: 2"' in html

    def test_discards_with_hand(self):
        html = _format("discards: 19m r4z\nhand: 123m (456p<)")

        assert 'class="mahjong-discards"' in html
        assert 'class="mahjong-hand-row"' in html


class TestConfigureSuperfences:
    def test_configure_applies_without_extension(self):
        configure_superfences(theme="dark")
        assert "mahjong-theme-dark" in _format("123m")

    def test_configure_applies_tile_back_color(self):
        configure_superfences(tile_back_color="#2e7d6b")
        assert 'style="--mahjong-tile-back: #2e7d6b"' in _format("123m")

    def test_configure_applies_table_color(self):
        configure_superfences(table_color="#2b7a78")
        out = _format("123m\nshimo.hand:")
        assert 'style="--mahjong-table-bg: #2b7a78"' in out
        assert "mahjong-table-filled" in out

    def test_rejected_configure_keeps_previous_config(self):
        configure_superfences(theme="dark")
        with pytest.raises(ValueError, match="tile_back_color"):
            configure_superfences(tile_back_color="url(x)")

        html = _format("123m")
        assert "mahjong-theme-dark" in html
        assert "mahjong-error" not in html
        assert "url(" not in html

    def test_configure_rejects_invalid_theme(self):
        with pytest.raises(ValueError, match="theme"):
            configure_superfences(theme="Dark")


class TestErrorBlock:
    def test_error_block(self):
        html = _error_block("<script>alert('xss')</script>")

        assert 'class="mahjong-error"' in html
        assert "<strong>Mahjong Error:</strong>" in html
        assert "&lt;script&gt;" in html
        assert "<script>" not in html


class TestTableBlock:
    def test_table_block_renders(self):
        html = _format("123m\nseat: south\ndora: 1z\nround: E1\nshimo.hand:\ntoimen.hand:\nkami.hand:")

        assert '<div class="mahjong-table">' in html
        assert html.count('class="mahjong-player ') == 4
        assert ">東一局</span>" in html

    def test_table_block_error(self):
        html = _format("123m\nshimo.hand: 15")

        assert 'class="mahjong-error"' in html
        assert "shimo: Invalid tile notation: 15 (did you forget a suit?)" in html
