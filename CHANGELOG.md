# Changelog

## [0.2.1] - 2026-06-04

### Changed

- fix: match `mj:` ONLY when it's delimited by a __single__ backtick

## [0.2.0] - 2026-06-04

### Added

- feat: backtick inline syntax `mj:...` to render tile groups or a whole hand inline.
- feat: `Xz` notation for a face-down tile (e.g. `:Xz:`).

### Changed

- css: style tiles with a depth/side face.
- css: slightly rounded corners; lighter tile background and border in dark mode.
- css: left-align the block with symmetric margins, right-justify called melds, and center the draw tile between the hand and the melds.
- css: scale the dora/ura/waits indicator row to 90%.

## [0.1.2] - 2026-05-08

### Added

- feat: add `waits` section after dora and ura.

### Changed

- refactor: rename `uradora` to `ura` throughout: `Hand.ura_indicators` field, `ura` block option key, CSS class `mahjong-ura`, and display label.
- Restyle dora/ura/waits indicator labels: stacked above tiles.

## [0.1.1] - 2026-03-16

### Changed

- docs: use `zensical.toml` instead of `mkdocs.yml` to configure Zensical for documentation.
- refactor: push extension config to superfences state eagerly in `extendMarkdown` instead of lazily in `superfences_validator`.
- refactor: use `parse_tiles()` instead of `parse()` for dora, uradora, and draw options in `apply_hand_options`.

### Removed

- feat: remove built-in `MahjongBlockProcessor` in favor of `pymdownx.superfences`.
- chore: remove `MahjongInlineProcessor` and `INLINE_TILE_PATTERN` from public API.
- chore: remove unused CSS hand size variant rules.
- chore: remove redundant `Hand.total_tile_count` property (use `len(hand.all_tiles)` instead).
- chore: remove unreachable `if not tiles` guard in `MahjongInlineProcessor.handleMatch`.

## [0.1.0] - 2026-02-09

- Initial release
