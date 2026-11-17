# fish-z

[English](README.md) | [简体中文](README.zh-CN.md)

**Remember the directories you use. Jump there with a few letters.**

fish-z is a directory jumping plugin for fish, maintained by
[BoringApp](https://github.com/BoringApp) and ported from
[agkozak/zsh-z v2.0.1](https://github.com/agkozak/zsh-z/tree/v2.0.1).
It brings zsh-z's core commands, frecency ranking, and text database format to
fish through native functions, events, and completions.

```fish
z launch           # Jump to the best matching directory
z project fish     # Match several terms in order
z -c src           # Search only beneath the current directory
z -l               # List the directories in your history
```

## Features

- Rank directories by a combination of visit frequency and recency, or use either separately.
- Prefer case-sensitive matches and fall back to case-insensitive matches; also support `ignore` and `smart` modes.
- Tab completion follows your search options and prioritizes directories with higher scores.
- Forget individual directories or entire subtrees, and prune directories that no longer exist.
- Exclude directory trees or keep entries for temporarily unavailable drives and mounts.
- Record visits in the background at each prompt, serialize writes with a directory lock, and replace the database atomically.
- Keep the database private with `0600` permissions and skip recording in fish private mode.

The runtime uses fish and standard macOS/Linux utilities. No Python, Node.js,
or compilation is required. Python is used only for the test suite.

## Installation

The target is fish 4.x. Development currently takes place on macOS with fish 4.9.3.
Run the following commands in a fish terminal. Choose either manual installation or Fisher.

Before enabling fish-z, disable any other plugin that defines `z`, including its
directory recording hooks. fish-z uses its own `FISHZ_*` settings. It does not read
the old fish plugin's `Z_*` variables or automatically import its history.

### Manual installation (recommended)

Clone the repository into a permanent location:

```fish
git clone https://github.com/BoringApp/fish-z.git ~/.local/share/fish-z/plugin
```

Add this line to `~/.config/fish/config.fish`:

```fish
source ~/.local/share/fish-z/plugin/fish-z.plugin.fish
```

Open a new fish terminal to start using the plugin. If no previous plugin is
running, you can also run the `source` command in your current interactive fish
session to load it immediately. You can keep the checkout elsewhere; adjust the
source path accordingly.

To update:

```fish
git -C ~/.local/share/fish-z/plugin pull --ff-only
```

Open a new terminal after updating to load the new functions.

### Install with Fisher

If you do not have [Fisher](https://github.com/jorgebucaran/fisher#installation), install it first:

```fish
curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
fisher install jorgebucaran/fisher
```

Install fish-z:

```fish
fisher install BoringApp/fish-z
```

Fisher installs the functions and startup configuration. No additional `source`
line in `config.fish` is needed.

To update:

```fish
fisher update BoringApp/fish-z
```

### Getting started

By default, history is stored at:

```text
$XDG_DATA_HOME/fish-z/data
```

If `XDG_DATA_HOME` is unset, the location is `~/.local/share/fish-z/data`.
A fresh installation starts with an empty history. Visit a few working
directories with `cd`, then use `z`.

## Commands

| Command | Behavior |
| --- | --- |
| `z` | List visited directories; do not change to Home |
| `z foo bar` | Match terms in order and jump to the best directory |
| `z -c foo` | Search only descendants of the current directory |
| `z -e foo` | Print the best match without changing directory |
| `z -l foo` | List matching directories and their scores |
| `z -r foo` | Select by visit frequency |
| `z -t foo` | Select by most recent visit |
| `z --add /path/to/dir` | Record a visit explicitly |
| `z -x` | Remove the current directory from history |
| `z -x /path/to/dir` | Remove a specified directory from history, even if it no longer exists |
| `z -xR /path/to/dir` | Remove the directory and its entire subtree from history |
| `z -- -name` | Search for a term beginning with `-` |
| `z -h` | Show help |

Removal affects only jump history. `z -xR /` asks for confirmation before clearing
the entire history. `-r` and `-t` cannot be combined. Searches return a nonzero
status when no match is found.

An existing absolute path can be used as a direct destination. If a history
search fails, fish-z also tries the requested relative directory. Quote paths
containing spaces when passing them to `--add` or `-x`.

By default, if one matching directory is an ancestor of every other match, fish-z
prefers that directory. With `FISHZ_UNCOMMON=1`, it selects the highest-scoring
directory and attempts to trim trailing components that do not contain the query.

## Configuration

For a manual installation, set options before sourcing the plugin:

```fish
set -g FISHZ_CASE smart
set -g FISHZ_EXCLUDE_DIRS /tmp /private/tmp
set -g FISHZ_KEEP_DIRS /Volumes/Work
set -g FISHZ_ECHO 1
source ~/.local/share/fish-z/plugin/fish-z.plugin.fish
```

For Fisher installations, you can save settings from an interactive fish using `set -U`:

```fish
set -U FISHZ_CASE smart
```

Open a new terminal afterward. This makes settings such as `FISHZ_CMD` available
before the plugin loads.

| Variable | Default | Purpose |
| --- | --- | --- |
| `FISHZ_CMD` | `z` | Command name; reload the plugin after changing it |
| `FISHZ_DATA` | See above | Absolute path to the database |
| `FISHZ_CASE` | Empty | Default case fallback, or `ignore` / `smart` |
| `FISHZ_COMPLETION` | `frecent` | Complete by score, or use `legacy` to sort by name |
| `FISHZ_CD` | `builtin cd` | Custom directory-changing command as a fish list, such as `set -g FISHZ_CD pushd` |
| `FISHZ_ECHO` | `0` | Print the current path after a jump |
| `FISHZ_TILDE` | `0` | Display the Home prefix as `~` |
| `FISHZ_EXCLUDE_DIRS` | Empty list | Do not record these directories or their descendants |
| `FISHZ_KEEP_DIRS` | Empty list | Keep these directory trees even when temporarily unavailable |
| `FISHZ_LOCK_TIMEOUT` | `1` | Seconds to wait for the write lock; fractions are allowed |
| `FISHZ_MAX_SCORE` | `9000` | Total score threshold that triggers aging |
| `FISHZ_NO_RESOLVE_SYMLINKS` | `0` | Set to `1` to preserve logical directory paths |
| `FISHZ_TRAILING_SLASH` | `0` | Set to `1` so `foo/` can also match a final `foo` path component |
| `FISHZ_UNCOMMON` | `0` | Trim the highest-scoring destination according to the query |

Directory lists use absolute paths and respect component boundaries: excluding
`/work` does not exclude `/workshop`.

## Writes and recovery

Each write reads, modifies, and replaces the database under the same directory
lock. Readers see a complete file from before or after the replacement. Normal
exit and the `TERM`, `INT`, and `HUP` signals clean up temporary files and the lock.
A lock timeout returns `2`. Automatic recording silently skips that visit;
running `z --add .` manually reports the error.

fish lacks zsh's built-in file-locking interface, so this port uses a directory
lock. A forced `kill -9` or power loss may leave `<database-path>.lock.d` behind.
Its `owner` file contains the writer's PID. After confirming that the process has
ended, delete the `owner` file and use `rmdir` to remove the empty lock directory.
The plugin does not take over a lock merely because it is old.

The database format is `absolute path|frequency|Unix timestamp`. Directory names
containing `|`, a newline, or a carriage return cannot be recorded. The database
may be a symlink; writes update its target while preserving the link.

## Differences from zsh-z

- Preserve the main user-facing commands without emulating zsh's ZLE, `zstyle`, or shell options.
- Queries support `*` and `?`, with whitespace acting as a wildcard, independently of `qmark-noglob`.
  The full zsh pattern language is not implemented.
- `-t` lists and completions both place the most recent visits first. Paths determine the order when scores tie.
- History is stored separately by default. Although the file format is shared, the directory lock and zsh-z's file lock are different mechanisms.
  Do not let both plugins write to the same database concurrently.
- zsh-z's `OWNER` setting for writes on behalf of another user is not provided. Windows is not supported.

## Development and tests

```sh
python3 -m unittest discover -s tests -v
```

Tests use a temporary Home and database. They do not read or modify your normal
shell's jump history. Optionally set
`ZSH_Z_REFERENCE=/path/to/zsh-z.plugin.zsh` to run behavioral comparisons with upstream.

## Authors and origins

- fish port and project maintenance: [BoringApp](https://github.com/BoringApp)
- Upstream implementation: [Alexandros Kozak / agkozak/zsh-z](https://github.com/agkozak/zsh-z)
- Original tool: [rupa/z](https://github.com/rupa/z)

fish-z is an independent fish port, not an official fish release of zsh-z.
It is distributed under the [MIT License](LICENSE), retaining the upstream
copyright notice and adding BoringApp's copyright for the port.
