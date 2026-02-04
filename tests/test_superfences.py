"""Tests for the superfences integration."""

import pytest

from pymdownx_mahjong.superfences import (
    _error_block,
    superfences_formatter,
    superfences_validator,
)


class TestSuperfencesValidator:
    """Tests for the superfences_validator function."""

    def test_validator_accepts_mahjong(self):
        """Test that validator accepts 'mahjong' language."""
        result = superfences_validator(
            language="mahjong",
            inputs={},
            options={},
            attrs={},
            md=None,
        )
        assert result is True

    def test_validator_rejects_other_languages(self):
        """Test that validator rejects other languages."""
        for lang in ["python", "javascript", "mermaid", "", "MAHJONG"]:
            result = superfences_validator(
                language=lang,
                inputs={},
                options={},
                attrs={},
                md=None,
            )
            assert result is False, f"Should reject language: {lang}"


class TestSuperfencesFormatter:
    """Tests for the superfences_formatter function."""

    def test_formatter_renders_simple_hand(self):
        """Test formatting a simple hand notation."""
        html = superfences_formatter(
            source="123m456p789s11222z",
            language="mahjong",
            class_name="",
            options={},
            md=None,
        )

        assert 'class="mahjong-hand"' in html
        assert 'data-tile="1m"' in html

    def test_formatter_with_yaml_options(self):
        """Test formatting with YAML-style options."""
        html = superfences_formatter(
            source="hand: 123m\ntitle: Test Hand",
            language="mahjong",
            class_name="",
            options={},
            md=None,
        )

        assert 'class="mahjong-hand"' in html
        assert "Test Hand" in html
        assert 'class="mahjong-caption"' in html

    def test_formatter_with_dora(self):
        """Test formatting with dora option."""
        html = superfences_formatter(
            source="hand: 123m456p789s11222z\ndora: 5m",
            language="mahjong",
            class_name="",
            options={},
            md=None,
        )

        assert 'class="mahjong-dora"' in html

    def test_formatter_with_draw(self):
        """Test formatting with draw option."""
        html = superfences_formatter(
            source="hand: 123m456p789s1112z\ndraw: 2z",
            language="mahjong",
            class_name="",
            options={},
            md=None,
        )

        assert 'class="mahjong-hand-draw"' in html

    def test_formatter_empty_notation(self):
        """Test formatting with empty notation."""
        html = superfences_formatter(
            source="",
            language="mahjong",
            class_name="",
            options={},
            md=None,
        )

        assert "mahjong-error" in html
        assert "No hand notation" in html

    def test_formatter_invalid_notation(self):
        """Test formatting with invalid notation."""
        html = superfences_formatter(
            source="8z9z",  # Invalid honor tile numbers
            language="mahjong",
            class_name="",
            options={},
            md=None,
        )

        assert "mahjong-error" in html

    def test_formatter_only_title_no_hand(self):
        """Test formatting with only title option (no hand)."""
        html = superfences_formatter(
            source="title: Only Title",
            language="mahjong",
            class_name="",
            options={},
            md=None,
        )

        assert "mahjong-error" in html


class TestErrorBlock:
    """Tests for the _error_block helper function."""

    def test_error_block_html_escaping(self):
        """Test that error messages are properly escaped."""
        html = _error_block("<script>alert('xss')</script>")

        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_error_block_structure(self):
        """Test error block HTML structure."""
        html = _error_block("Test error message")

        assert 'class="mahjong-error"' in html
        assert "<strong>Mahjong Error:</strong>" in html
        assert "Test error message" in html
