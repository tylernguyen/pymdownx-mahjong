"""Tests for the superfences integration."""

from pymdownx_mahjong.superfences import (
    _error_block,
    superfences_formatter,
    superfences_validator,
)


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

        assert 'class="mahjong-hand"' in html
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


class TestErrorBlock:
    def test_error_block(self):
        html = _error_block("<script>alert('xss')</script>")

        assert 'class="mahjong-error"' in html
        assert "<strong>Mahjong Error:</strong>" in html
        assert "&lt;script&gt;" in html
        assert "<script>" not in html
