# Reference

[English](reference.md) | [简体中文](reference.zh-CN.md) · [Back to README](../README.md)

## History location

History is stored at `$XDG_DATA_HOME/fish-z/data`, falling back to
`~/.local/share/fish-z/data` when `XDG_DATA_HOME` is unset.

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
set -g FISHZ_CASE ignore
set -g FISHZ_EXCLUDE_DIRS /tmp /private/tmp
set -g FISHZ_KEEP_DIRS /Volumes/Work
set -g FISHZ_ECHO 1
source ~/.local/share/fish-z/plugin/fish-z.plugin.fish
```

For Fisher installations, you can save settings from an interactive fish using `set -U`:

```fish
set -U FISHZ_CASE ignore
```

Open a new terminal afterward. This makes settings such as `FISHZ_CMD` available
before the plugin loads.

| Variable | Default | Purpose |
| --- | --- | --- |
| `FISHZ_CMD` | `z` | Command name; reload the plugin after changing it |
| `FISHZ_DATA` | See above | Absolute path to the database |
| `FISHZ_CASE` | `smart` | Case matching: `smart`, `ignore`, or `fallback` |
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

`smart` ignores case for lowercase queries and matches case exactly when a query
contains uppercase letters. `ignore` always ignores case. `fallback` preserves
the original behavior: prefer case-sensitive matches, then ignore case if none
are found. Unset or empty `FISHZ_CASE` uses `smart`.

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

- Smart case is the default. Set `FISHZ_CASE=fallback` for zsh-z's default case preference.
- Preserve the main user-facing commands without emulating zsh's ZLE, `zstyle`, or shell options.
- Queries support `*` and `?`, with whitespace acting as a wildcard, independently of `qmark-noglob`.
  The full zsh pattern language is not implemented.
- `-t` lists and completions both place the most recent visits first. Paths determine the order when scores tie.
- History is stored separately by default. Although the file format is shared, the directory lock and zsh-z's file lock are different mechanisms.
  Do not let both plugins write to the same database concurrently.
- zsh-z's `OWNER` setting for writes on behalf of another user is not provided. Windows is not supported.
