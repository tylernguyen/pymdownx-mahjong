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

- Inline rendering of individual Mahjong tiles and melds.
- Figure rendering of a __complete__ game state: multiple hands, discards, scores, dora, round, and seat information.
- Figure rendering of an individual Mahjong hand (including melds), with discards and accompanying information.
- Adaptive tile assets, with customizations for tile back and background color. 

## Installation

> [!warning] Dependency
> [SuperFences](https://facelessuser.github.io/pymdown-extensions/extensions/superfences/) :lucide-arrow-up-right: from PyMdown Extensions.

```bash
pip install pymdownx-mahjong
```

Copy [mahjong.css :lucide-arrow-up-right:](https://github.com/tylernguyen/pymdownx-mahjong/releases) to `stylesheets/`.

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
| enable_inline    | bool | `true` `false`  | `true`  | render `:1m:` and `` `mj:` `` inline syntax |
| closed_kan_style | str  | `outer` `inner` | `outer` | `outer`: back, front, front, back `inner`: front, back, back, front |
| tile_back_color  | str  | CSS color       | `#e7b246` | color of tiles' backs, e.g. `#2e7d6b` |
| table_color      | str  | CSS color       | transparent | color of tablecloth, e.g. `#2b7a78` |


## Basic Syntax

### Tile Syntax

The extension uses standard MPSZ notation, and extends on it with the __Xz__ notation for an unknown tile.

| Syntax | Tile                 | Render   |
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

### Meld Syntax

- Parenthesis `()` for open melds. `<` `^` `>` to indicate direction of meld.
- Brackets `[]` for closed melds.
- `+` in a Pon to indicate an added Kan.

| Syntax                              | Description | Render                                       |
|-------------------------------------|-------------|----------------------------------------------|
| `(046m<)` `(978p<)`                 | Chi         | `mj:(046m<)` `mj:(978p<)`                    |
| `(550m<)` `(505p^)` `(055s>)`       | Pon         | `mj:(550m<)` `mj:(505p^)` `mj:(055s>)`       |
| `[5555m]` `[0555p]`                 | Closed Kan  | `mj:[5555m]` `mj:[0555p]`                    |
| `(555+0m<)` `(550+5p^)` `(550+5s>)` | Added Kan   | `mj:(555+0m<)` `mj:(550+5p^)` `mj:(550+5s>)` |

### Discard Syntax

Add `discards:` to a block to render a discard pile above the hand.

| Syntax | Title                         | Example |
| ------ | ----------------------------- | ------- |
| `r`    | Riichi marker (sideway)       | `r1m`   |
| `t`    | Tsumogiri (dimmed)            | `t1m`   |
| `c`    | Called by another player      | `c1m`   |

Syntax can be combined, `rt5p` is tsumogiri riichi, `cr5p` is a riichi tile that has been called.

Every discard after the riichi tile is tsumogiri, so it's dimmed without needing `t`.

Discards can be single-line or formatted into multi-indented lines for easier reference.

````markdown
```mahjong
discards: 4z 9m t9p 6z t5z 2s t9m 5m 6s tc2p t9p t9p 1m 9m 4m 5z
```
````

````markdown
```mahjong
discards: 
  4z 9m t9p 6z t5z 2s
  t9m 5m 6s tc2p t9p t9p
  1m 9m 4m 5z
```
````

## Inline Syntax

Render tiles inline individually by using their shortname, e.g. `:1p:` will render as :1p:.

Additionally, you can render tile groups or entire hand inline using the prefix `mj:`. 

``mj:(123m<)(111z^) 456789m`` will render `mj:(123m<)(111z^) 456789m`.

## Figure Syntax

Figures are written in a `mahjong` fenced code block, with additional options to convey info.

- default hand can be written without an option but also accepts `hand` as an option.
- `dora`: renders dora indicator(s) as a dead-wall block.
- `riichi`: indicate number of riichi sticks in the pot.
- `round`: round wind and hand number, e.g. `S2`. Can include the honba instead of a `honba` option, e.g. `S2-1`.
- `honba`: if honba info is not written in round, this can explicitly set it
- `remaining`: indicate live tiles remaining in the wall, or `auto` to count them on a full table render.
- `seat` and `score`: wind marker and score. Score shows delta from starting on hover. It also supports loans, `7000(10000)` is 7000 after borrowing 10000. The loan shows beside the delta on hover.
- `starting_score`: what every player in the figure started with, `25000` by default.
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

### Additional Figure Syntax

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
discards: 
  4z 9m t9p 6z t5z 2s
  t9m 5m 6s tc2p t9p t9p
seat: east
score: 23800
riichi: 1
honba: 1
shimo.score: 41000
shimo.hand: (234p<) (777z^)
shimo.discards: 
  1m 2z 9s 5z 3s 6m
  4m c4p 1m t6z 4m t8p
  t4z
toimen.score: 17900
toimen.hand: (456p<)
toimen.discards: 
  9s 1s 6z 2m 5s t2s
  t6m 8p 3m t5z 4m 8p
  9p
kami.score: 16300
kami.discards: 
  1m t9s 1z 2z c7z 3m
  5p rc6m rt4s t5z t7m t7p
  t6p
```
````

```mahjong
title: M-League 26-27 10/1 Table 1
round: S2
remaining: auto
dora: 2z
hand: 11p888s11133z (640m<)
draw: 1p
discards: 
  4z 9m t9p 6z t5z 2s
  t9m 5m 6s tc2p t9p t9p
seat: east
score: 23800
riichi: 1
honba: 1
shimo.score: 41000
shimo.hand: (234p<) (777z^)
shimo.discards: 
  1m 2z 9s 5z 3s 6m
  4m c4p 1m t6z 4m t8p
  t4z
toimen.score: 17900
toimen.hand: (456p<)
toimen.discards: 
  9s 1s 6z 2m 5s t2s
  t6m 8p 3m t5z 4m 8p
  9p
kami.score: 16300
kami.discards: 
  1m t9s 1z 2z c7z 3m
  5p rc6m rt4s t5z t7m t7p
  t6p
```
