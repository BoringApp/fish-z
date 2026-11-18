# Repository guidance

These instructions apply to the entire fish-z repository.

## Project and layout

fish-z is BoringApp's native fish port of agkozak/zsh-z. The current behavioral
reference is upstream v2.0.1. Target fish 4.x on macOS/Linux; macOS with fish 4.9.3
is the verified development environment. Do not claim Linux validation unless it ran.

- `fish-z.plugin.fish`: entry point for sourcing a manual checkout.
- `conf.d/fish-z.fish`: command registration, completions, and interactive event hooks.
  Fisher installs this snippet directly, without the root entry point.
- `functions/fishz.fish`: public command parsing and directory changes.
- `functions/__fishz_query.fish`: matching, scoring, selection, and listing.
- `functions/__fishz_record.fish`: launch and coordinate isolated writer processes.
- `functions/__fishz_write.fish`: locked database transactions and cleanup.
- `functions/__fishz_util.fish`: paths, database records, and shared helpers.
- `functions/__fishz_complete.fish`: fish completion adapter.
- `tests/test_fish_z.py`: Python standard-library integration tests.

Keep the runtime in fish with standard system utilities. Python belongs to the
tests, not the plugin runtime. Locate helpers relative to their installed files;
support both a manual checkout and Fisher's copied directory layout.

## Behavior to preserve

- Use `FISHZ_*` settings. There is no compatibility layer for the old fish plugin's `Z_*` settings.
- Unset or empty `FISHZ_CASE` defaults to `smart`: lowercase queries ignore case;
  uppercase queries match case exactly. `ignore` always ignores case; `fallback`
  preserves upstream's case-sensitive-first behavior. Match upstream test modes explicitly.
- After case filtering, rank matches by basename: exact, prefix, substring, then
  parent-path-only. The final nonempty query term (or its last path component)
  determines the level. Apply frecency, `-r`, or `-t` scores only within a level.
  Common ancestors must not override the chosen destination. Default completion
  follows the same ranking; explicit `legacy` completion remains alphabetical.
- Bare `z` lists history; `-c` restricts searches to descendants, not database cleanup.
- Treat `-r` and `-t` as mutually exclusive. Stop on invalid arguments.
- Listing, echoing, and completion must not change directories or write history.
  Completion must remain read-only even when arguments include `--add` or `-x`.
- Match and remove directory trees by component boundaries, not raw string prefixes.
  Treat paths as data, including spaces, Unicode, dollar signs, backslashes, and brackets.
- Keep the `*` / `?` query behavior independent of fish's `qmark-noglob` flag.
- Preserve completion order with `complete -k`; do not double-escape inserted paths.
- `FISHZ_CMD=fishz` must not create a wrapper that calls itself.
- Keep prompt recording asynchronous. Finish this shell's pending add before an
  explicit removal, and suppress re-recording until the user changes directory.
- Keep the documented differences from upstream explicit instead of claiming full equivalence.

## Database and process rules

The format is `absolute path|frequency|Unix timestamp`. Default storage is
`$XDG_DATA_HOME/fish-z/data`, falling back to `~/.local/share/fish-z/data`.

- Hold `<database>.lock.d` over the whole read/modify/replace transaction.
  Write through a temporary file in the same directory and publish only after success.
- Preserve `0600` database permissions and symlinked database targets, including
  links whose targets do not exist yet.
- Bound lock waits and keep lock timeout status `2`. Do not reclaim a lock by age.
- Signal handlers mark cancellation; ordinary control flow returns the error and
  the worker's `fish_exit` handler cleans up. Direct `exit` inside a signal handler
  was observed to lose the intended exit status on the development fish build.
- Handle zero records explicitly. Do not use an unchecked `seq 0` as an array index
  generator: fish arrays start at 1.
- Reject paths that the format cannot represent. Ignore malformed stored rows
  without executing or interpreting them as shell code.
- Do not silently share writes with zsh-z: its lock protocol differs from ours.

## Validation

Run behavior changes from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

For changes intended to match upstream, also run the optional comparisons against
an available v2.0.1 reference:

```sh
ZSH_Z_REFERENCE=/path/to/zsh-z.plugin.zsh python3 -m unittest discover -s tests -v
```

Without that variable, the comparison tests are skipped; do not report them as passed.
Add regression coverage for behavior being changed rather than tests that repeat
implementation details. Run syntax checks with `fish --no-config --no-execute`.

Tests must use temporary `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, and `FISHZ_DATA`.
The test harness explicitly sets `fish_private_mode=0` only inside that isolated
environment; test private mode separately. Do not use a contributor's actual
shell configuration or history as test fixtures.

For startup or installation code changes, check both installation layouts in an
isolated configuration. For documentation-only changes, check local links, shell
snippet syntax, language consistency, and `git diff --check`; no full test rerun is needed.

## Documentation and contributions

- `README.md` is the default English documentation; `README.zh-CN.md` is Simplified Chinese.
  Keep commands, settings, limitations, and language switch links synchronized.
- Document manual installation first and Fisher second. Both are supported choices.
- Keep machine-specific paths, history databases, credentials, and test caches out of commits.
- Preserve the MIT license and both BoringApp's and Alexandros Kozak's copyright notices.
- Keep changes within the requested scope. An installation or history import requires
  a request for that action; a source change alone is not an instruction to modify a live shell.
