# fish-z

[English](README.md) | [简体中文](README.zh-CN.md)

A native fish port of [zsh-z](https://github.com/agkozak/zsh-z), my favorite command in Zsh.

It remembers the directories you visit and lets you jump back with a few letters.

## Installation

Requires fish 4.x. Disable any other `z` plugin before installing.

### Manual installation (recommended)

```fish
git clone https://github.com/BoringApp/fish-z.git ~/.local/share/fish-z/plugin
```

Add this line to `~/.config/fish/config.fish`, then open a new terminal:

```fish
source ~/.local/share/fish-z/plugin/fish-z.plugin.fish
```

To update, run the following command and open a new terminal:

```fish
git -C ~/.local/share/fish-z/plugin pull --ff-only
```

### Fisher

With [Fisher](https://github.com/jorgebucaran/fisher#installation) installed:

```fish
fisher install BoringApp/fish-z
```

To update:

```fish
fisher update BoringApp/fish-z
```

## Usage

Visit a few directories with `cd`; fish-z remembers them automatically.

```fish
z foo          # Jump to the best match
z foo bar      # Match several terms in order
z -c foo       # Search beneath the current directory
z -l foo       # List matches and their scores
```

Press **Tab** to complete matching directories. Searches use smart case:
lowercase queries ignore case; queries containing uppercase letters match case exactly.

Run `z -h` for more commands. Advanced options are in the [reference](docs/reference.md).

## Benchmark

Query and completion latency with 1,000 directory records on an Apple Silicon Mac:
fish 4.9.3, zsh 5.9, zsh-z v2.0.1. Each value is the median of five batches of
three calls in an already running shell; shell startup is excluded.

| Operation | fish-z | zsh-z |
| --- | ---: | ---: |
| Query matching one directory | 15.77 ms | 40.45 ms |
| Query matching all directories | 104.89 ms | 43.54 ms |
| Generate all completion candidates | 107.10 ms | 51.60 ms |

[Benchmark script and instructions](tests/benchmark_fish_z.py).

## Credits

Maintained by [BoringApp](https://github.com/BoringApp), based on
[Alexandros Kozak's zsh-z](https://github.com/agkozak/zsh-z) and
[rupa/z](https://github.com/rupa/z).
[MIT License](LICENSE), with the upstream copyright notice retained.
