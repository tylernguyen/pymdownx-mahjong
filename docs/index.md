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

PyMdown Mahjong is an extension for Python Markdown that aids writing Mahjong content. Designed with MkDocs and Zensical in mind, the extension offers:

- Inline rendering of individual Mahjong tiles.
- Complete Mahjong hand rendering, supporting: pon/chi/kan, and dora information.

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


## Inline Syntax

Inline tiles individually by using their shortname, e.g. `:1p:` will render as :1p:.

Additionally, you can render tile groups or entire hand inline using the prefix `mj:`. 

For example, ``mj:123456789m`` will render `mj:123456789m` inline.

> [!failure] Inline Melds
> Currently, the renderer does __NOT__ support inline melds.

## Block Syntax

Hands are written in a fenced codeblock, with additional YAML-like options for dora, uradora, and title.

````markdown
```mahjong
5511122z [3333z] (444+4z>)
draw: 2z
waits: 52z
dora: 5z
title: Daisuushii Tsuuiisou
```
````

```mahjong
5511122z [3333z] (444+4z>)
draw: 2z
waits: 52z
dora: 5z
title: Daisuushii Tsuuiisou
```

## Syntax for Melds

Parenthesis `()` for open melds. `<` `^` `>` to indicate direction of meld.

- `(123m<)` - Chi from kamicha
- `(111m<)` - Pon from kamicha
- `(111p^)` - Pon from toimen
- `(999s>)` - Pon from shimocha

Brackets `[]` for closed kan.

- `[1111z]` - Closed kan

Additional sign `+` to indicate added kan.

- `(666+6z^)` - Added Kan

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
