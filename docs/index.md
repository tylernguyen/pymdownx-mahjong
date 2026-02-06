---
icon: octicons/markdown-16
---

# PyMdown Mahjong

## Purpose

PyMdown Mahjong is an extension for Python Markdown that aids writing Mahjong content. Designed with MkDocs and Zensical in mind, the extension offers:

- Inline rendering of individual Mahjong tiles.
- Complete Mahjong hand rendering, supporting: pon/chi/kan, and dora information.

## Installation

```bash
pip install pymdownx-mahjong
```

Copy `mahjong.css` to `stylesheets/`.

=== "`zensical.toml`"

    ```toml
    [project.markdown_extensions.pymdownx_mahjong]
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
      - pymdownx_mahjong
      - pymdownx.superfences:
          custom_fences:
            - name: mahjong
              class: mahjong
              validator: !!python/name:pymdownx_mahjong.superfences_validator
              format: !!python/name:pymdownx_mahjong.superfences_formatter

    extra_css:
      - stylesheets/mahjong.css
    ```


### Configuration

| Key              | Type | Options         | Default | Description                                                         |
|------------------|------|-----------------|---------|---------------------------------------------------------------------|
| theme            | str  | `auto` `light` `dark` | `auto` |  |
| closed_kan_style | str  | `outer` `inner` | `outer` | `outer`: back, front, front, back `inner`: front, back, back, front |


### MPSZ Notation

The extension uses standard MPSZ notation for tiles.

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

### Hand Syntax

Hands are written in a fenced codeblock, with additional YAML-like options for dora, uradora, and title.

~~~markdown
```mahjong
hand: 123m456p789s11z
dora: 2m
uradora: 2m
title: "Pinfu"
```
~~~

### Syntax for Melds

Parenthesis `()` for open melds. `<` `^` `>` to indicate direction of meld.

- `(123m<)` - Chi from kamicha
- `(111m<)` - Pon from kamicha
- `(111p^)` - Pon from toimen
- `(999s>)` - Pon from shimocha

Brackets `[]` for closed kan.

- `[1111z]` - Closed kan

Additional sign `+` to indicate added kan.

- `(666+6z^)` - Added Kan
