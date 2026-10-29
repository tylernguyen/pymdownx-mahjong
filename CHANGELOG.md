# Changelog

## [0.2.3] - 2026-10-29

### Added

- feat: `discards:` block option renders a discard pile (rows of 6, 6, rest) above an optional hand, with `r` (riichi), `t` (tsumogiri) and `c` (called) markers.

### Changed

- fix: align sideways tiles' 3D edge with upright tiles.
- fix: fenced blocks use their own Markdown instance's config; it overrides `configure_superfences()`.
- fix: raise `ValueError` on invalid `theme` or `closed_kan_style`.
- fix: keep unpaired quotes in block options (`title: The players'`).
- docs: register `pymdownx_mahjong` alongside SuperFences.
- refactor: stateless parser; remove unused constants.
- chore: single-source version; add Python 3.14.
- chore(CI): run pytest and mypy.
- chore(CI): add ruff format and lint checks

## [0.2.2] - 2026-10-14

### Added

- feat(a11y): label tiles (`role="img"`, `aria-label`), face-down tiles, melds, the draw tile, and uncaptioned hands for screen readers.

### Changed

- perf: emit each tile's SVG once per page as a `<symbol>` and reference it with `<use>`, instead of inlining the full SVG for every tile (and twice with `theme: auto`).
- fix: deterministic SVG IDs, so rebuilding a page produces identical HTML.
- chore(CI): only publish to PyPI from a published release
- fix: reject invalid melds: pon/kan of non-identical tiles, chi called from `^` or `>`, added kan without a source marker, and closed melds that aren't a kan.
- fix: count red 5s toward the 4-per-tile limit (`55550m` is now an error).
- fix: count the `draw:` tile toward the 4-per-tile limit, and reject a `draw:` of more than one tile.
- fix: reject unknown block options (e.g. `doras:`) and a second hand notation line instead of silently ignoring them.
- chore: add tests for extension and renderer

## [0.2.1] - 2026-06-04

### Changed

- css: center render when there are no melds
- fix: restrict X as a tile of the z suit
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
- css: restyle dora/ura/waits indicator labels: stacked above tiles.

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
