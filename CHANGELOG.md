# Changelog

## [1.2.1] - 2026-02-04

### Removed

- **inline_svg config option**: enforce inline SVG

## [1.2.0] - 2026-02-04

### Added

- **Closed Kan Style Option**: New `closed_kan_style` configuration option to control back tile placement in closed kan:
  - `'outer'` (default): back tiles on edges (back, front, front, back)
  - `'inner'`: back tiles in middle positions (front, back, back, front)

- **Superfences Configuration API**: New `configure_superfences()` function for programmatic configuration of superfences integration.

### Changed

- **Superfences Config Inheritance**: Superfences formatter now auto-detects and inherits configuration from the main `pymdownx_mahjong` extension.

- **YAML Config Compatibility**: Boolean config options (`inline_svg`, `enable_inline`) now use string defaults for proper YAML parsing in MkDocs. Added `_to_bool()` helper for string-to-boolean conversion.

### Removed

- **show_labels config option**: Tile title attributes are now always shown. 
- **css_class config option**: CSS class is now fixed to 'mahjong-hand' for blocks and 'mahjong-inline' for inline tiles. 

## [1.1.0] - 2026-02-04

### Added

- **SVG Caching**: Module-level LRU cache (`@functools.lru_cache(maxsize=128)`) for SVG file loading via `_load_svg_from_package()` function in `renderer.py`. This significantly improves performance when rendering multiple tiles by eliminating repeated file I/O for package assets.

- **Tile Count Validation**: `_validate_tile_counts()` method in `MahjongParser` that validates hands don't contain more than 4 copies of any tile (which is impossible in real Mahjong). Raises `ParseError` with a descriptive message when violated.

- **New Tests**:
  - `tests/test_renderer.py` - 21 tests covering rendering, configuration, themes, melds, and SVG ID uniqueness
  - `tests/test_superfences.py` - 11 tests covering validator, formatter, and error handling
  - `tests/test_utils.py` - 20 tests covering `parse_block_content()` and `apply_hand_options()`
  - Added 11 new tests for tile count validation in `tests/test_parser.py`

### Changed

- **Type Annotations**: Improved type safety with `typing.Final` and `typing.Pattern` annotations:
  - `tiles.py`: `TILE_DATABASE` and `SPECIAL_TILES` now typed as `Final[...]`
  - `parser.py`: `TILE_GROUP_PATTERN` and `MELD_PATTERN` now typed as `Final[Pattern[str]]`
  - `renderer.py`: All 7 regex patterns now typed as `Final[Pattern[str]]`
  - `inline.py`: `INLINE_TILE_PATTERN` now typed as `Final[str]`

- **SVG Loading**: Refactored `_load_svg()` method to use the new cached `_load_svg_from_package()` function for package assets while maintaining uncached behavior for custom asset paths.

### Removed

- **Code Cleanup**: Removed redundant instance-level `_svg_cache` dict (now using module-level LRU cache). Simplified `_process_svg()` by removing unused `unique_prefix` parameter.

### Fixed

- `test_hand_properties` now uses non-conflicting tile types (2222z instead of 1111z with 11z closed) to properly test hand properties without triggering tile count validation.

## [1.0.0] - 2026-02-04

### Added

- Initial release
- MPSZ notation parser for Riichi Mahjong hands
- HTML renderer with inline SVG tiles
- Support for melds (chi, pon, kan, added kan)
- Light/dark/auto theme support
- Python Markdown extension integration
- Superfences custom fence support
- Inline tile syntax (`:1m:`)
- Dora and uradora indicator support
- Draw tile specification
