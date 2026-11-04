---
icon: octicons/markdown-16
---

# PyMdown Mahjong

```mahjong
19p19s19m1234567Xz
```

> [!warning] LLM Assistance
> This project was written with assistance from :simple-claude:{ .claude } Claude. If that's a deal-breaker for you, I understand.

## Purpose

PyMdown Mahjong is an extension for Python Markdown that aids writing Mahjong content. Designed and tested for Zensical, the extension offers:

- Inline rendering of individual Mahjong tiles.
- Complete Mahjong hand rendering, supporting: pon/chi/kan, and dora information.
- Discard pile rendering.
- Other players' hands and discards, laid out around the table.

## Dependency

[SuperFences](https://facelessuser.github.io/pymdown-extensions/extensions/superfences/) :lucide-arrow-up-right: from PyMdown Extensions.

## Installation

```bash
pip install pymdownx-mahjong
```

Copy `mahjong.css` to `stylesheets/`.

=== "`zensical.toml`"

    ```toml
    [project.markdown_extensions.pymdownx_mahjong]
    theme = "auto"
    closed_kan_style = "outer"
    tile_back_color = "#e7b246"
    table_color = ""
    [project.markdown_extensions.pymdownx.superfences]
    custom_fences = [
      { name = "mahjong", class = "mahjong", format = "pymdownx_mahjong.superfences_formatter" }
    ]

    [project]
    extra_css = ["stylesheets/mahjong.css"]
    ```

=== "`mkdocs.yml`"

    ```yaml
    markdown_extensions:
      - pymdownx_mahjong:
          theme: auto
          closed_kan_style: outer
          tile_back_color: "#e7b246"
          table_color: ""
      - pymdownx.superfences:
          custom_fences:
            - name: mahjong
              class: mahjong
              validator: !!python/name:pymdownx_mahjong.superfences_validator
              format: !!python/name:pymdownx_mahjong.superfences_formatter

    extra_css:
      - stylesheets/mahjong.css
    ```


> [!note]
> Register `pymdownx_mahjong` alongside SuperFences even if you only use fenced blocks. The extension supplies the fence's `theme`, `closed_kan_style`, `tile_back_color` and `table_color`, and emits each tile's artwork once per page. Without it, every block embeds its own copy, producing duplicate element IDs.

### Configuration

| Key              | Type | Options         | Default | Description                                                         |
|------------------|------|-----------------|---------|---------------------------------------------------------------------|
| theme            | str  | `auto` `light` `dark` | `auto` |  |
| closed_kan_style | str  | `outer` `inner` | `outer` | `outer`: back, front, front, back `inner`: front, back, back, front |
| tile_back_color  | str  | CSS color       | `#e7b246` | color of tiles' backs, e.g. `#2e7d6b` |
| table_color      | str  | CSS color       | transparent | color of tablecloth, e.g. `#2b7a78` |


## Inline Syntax

Inline tiles individually by using their shortname, e.g. `:1p:` will render as :1p:.

Additionally, you can render tile groups or entire hand inline using the prefix `mj:`. 

For example, ``mj:123456789m`` will render `mj:123456789m` inline.

> [!failure] Inline Melds
> Currently, the renderer does __NOT__ support inline melds.

## Block Syntax

Hands are written in a `mahjong` fenced code block, with additional options to convey info.

- default hand can be written without an option but also accepts `hand` as an option.
- `dora`: renders dora indicator(s) as a dead-wall block.
- `riichi`: indicate number of riichi sticks in the pot.
- `round`: round wind and hand number, e.g. `S2`. Can include the honba instead of a `honba` option, e.g. `S2-1`.
- `honba`: if honba info is not written in round, this can explicitly set it
- `remaining`: indicate live tiles remaining in the wall, or `auto` to count them on a full table render.
- `seat` and `score`: wind marker and score.
- `title`: title for the rendered figure.

````markdown
```mahjong
5511122z [3333z] (444+4z>)
draw: 2z
discards: 123456m123456p123456s567z
round: S2
remaining: 2
score: 20000
dora: 0m 0p 0s
riichi: 1
honba: 1
seat: east
title: Daisuushii Tsuuiisou
```
````

```mahjong
5511122z [3333z] (444+4z>)
draw: 2z
discards: 123456m123456p123456s567z
round: S2
remaining: 2
score: 20000
dora: 0m 0p 0s
riichi: 1
honba: 1
seat: east
title: Daisuushii Tsuuiisou
```

### Additional Block Syntax

To render a complete board-state, `hand`, `discards`, and `score` can be affixed with `kami.`, `shimo.`, and `toimen.`;

Other players' seat wind are automatically generated from any `seat`. Likewise, round wind marker placement is generated from `seat` and `round`.

`remaining: auto` counts the tiles left in the wall from the discards, melds, and kans.

````markdown
```mahjong
title: M-League 26-27 10/1 Table 1
round: S2
remaining: auto
dora: 2z
hand: 11p888s11133z (640m<)
draw: 1p
discards: 4z 9m t9p 6z t5z 2s t9m 5m 6s tc2p t9p t9p
seat: east
score: 23800
riichi: 1
honba: 1
shimo.score: 41000
shimo.hand: (234p<) (777z^)
shimo.discards: 1m 2z 9s 5z 3s 6m 4m c4p 1m t6z 4m t8p t4z
toimen.score: 17900
toimen.hand: (456p<)
toimen.discards: 9s 1s 6z 2m 5s t2s t6m 8p 3m t5z 4m 8p 9p
kami.score: 16300
kami.discards: 1m t9s 1z 2z c7z 3m 5p rc6m rt4s t5z t7m t7p t6p
```
````

```mahjong
title: M-League 26-27 10/1 Table 1
round: S2
remaining: auto
dora: 2z
hand: 11p888s11133z (640m<)
draw: 1p
discards: 4z 9m t9p 6z t5z 2s t9m 5m 6s tc2p t9p t9p
seat: east
score: 23800
riichi: 1
honba: 1
shimo.score: 41000
shimo.hand: (234p<) (777z^)
shimo.discards: 1m 2z 9s 5z 3s 6m 4m c4p 1m t6z 4m t8p t4z
toimen.score: 17900
toimen.hand: (456p<)
toimen.discards: 9s 1s 6z 2m 5s t2s t6m 8p 3m t5z 4m 8p 9p
kami.score: 16300
kami.discards: 1m t9s 1z 2z c7z 3m 5p rc6m rt4s t5z t7m t7p t6p
```

## Meld Syntax

Parenthesis `()` for open melds. `<` `^` `>` to indicate direction of meld.

- `(123m<)` - Chi from kamicha
- `(111m<)` - Pon from kamicha
- `(111p^)` - Pon from toimen
- `(999s>)` - Pon from shimocha

Brackets `[]` for closed kan.

- `[1111z]` - Closed kan

Additional sign `+` to indicate added kan.

- `(666+6z^)` - Added Kan

## Discard Syntax

Add `discards:` to a block to render a discard pile above the hand.

Syntax can be combined, `rt5p` is tsumogiri riichi on :5p:.

Every discard after the riichi tile is tsumogiri, so it's dimmed without needing `t`.

| Syntax | Title                         | Example |
| ------ | ----------------------------- | ------- |
| `r`    | Riichi marker                 | `r1m`   |
| `t`    | Tsumogiri (dimmed)            | `t1m`   |
| `c`    | Called by another player      | `c1m`   |

## Tile Notation

The extension uses standard MPSZ notation, and extends on it with the __Xz__ notation for an unknown tile.

| Notation | Tile                 | Tile (Emoji)   |
| -------- | -------------------- | -------------- |
| `1m`, `2m`, ...  | Manzu        | :1m: :2m: :3m: |
| `1p`, `2p`, ...  | Pinzu        | :1p: :2p: :3p: |
| `1s`, `2s`, ...  | Souzu        | :1s: :2s: :3s: |
| `0m` `0p` `0s`   | Akadora      | :0m: :0p: :0s: |
| `1z`     | East / Ton           | :1z:           |
| `2z`     | South / Nan          | :2z:           |
| `3z`     | West / Sha           | :3z:           |
| `4z`     | North / Pei          | :4z:           |
| `5z`     | White Dragon / Haku  | :5z:           |
| `6z`     | Green Dragon / Hatsu | :6z:           |
| `7z`     | Red Dragon / Chun    | :7z:           |
| `Xz`     | Unknown              | :Xz:           |
