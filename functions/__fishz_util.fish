# Shared helpers for fish-z. Calling __fishz_util autoloads this file.
function __fishz_util
end

function __fishz_under --argument-names candidate root
    set root (path normalize -- "$root")
    test "$candidate" = "$root"; and return 0
    test "$root" = /; and string match -q '/*' -- "$candidate"; and return 0
    set -l prefix "$root/"
    test (string sub -l (string length -- "$prefix") -- "$candidate") = "$prefix"
end

function __fishz_keep --argument-names candidate
    test -d "$candidate"; and return 0
    for root in $FISHZ_KEEP_DIRS
        __fishz_under "$candidate" "$root"; and return 0
    end
    return 1
end

function __fishz_path --argument-names target
    string match -q '/*' -- "$target"; or set target "$PWD/$target"
    if test "$FISHZ_NO_RESOLVE_SYMLINKS" = 1
        path normalize -- "$target"
    else
        path resolve -- "$target"
    end
    # path resolve/normalize return 1 when their input is already canonical.
    return 0
end

function __fishz_display --argument-names target
    if test "$FISHZ_TILDE" = 1; and __fishz_under "$target" "$HOME"
        printf '~%s\n' (string sub -s (math (string length -- "$HOME") + 1) -- "$target")
    else
        printf '%s\n' "$target"
    end
end

function __fishz_data
    set -l data "$HOME/.local/share/fish-z/data"
    if set -q XDG_DATA_HOME[1]; and test -n "$XDG_DATA_HOME"
        set data "$XDG_DATA_HOME/fish-z/data"
    end
    if set -q FISHZ_DATA[1]; and test -n "$FISHZ_DATA"
        set data "$FISHZ_DATA"
    end
    if not string match -q '/*' -- "$data"
        printf 'fish-z: FISHZ_DATA must be an absolute path\n' >&2
        return 1
    end
    if test -d "$data"
        printf 'fish-z: database is a directory: %s\n' "$data" >&2
        return 1
    end
    # path resolve leaves a dangling final symlink unresolved on some fish
    # versions. Follow that link explicitly before replacing the target file.
    set -l links 0
    while test -L "$data"
        if test "$links" -ge 40
            printf 'fish-z: database symlink loop: %s\n' "$data" >&2
            return 1
        end
        set -l destination (command readlink -- "$data")
        or return 1
        if string match -q '/*' -- "$destination"
            set data "$destination"
        else
            set data (path dirname -- "$data")/"$destination"
        end
        set data (path normalize -- "$data")
        set links (math "$links + 1")
    end
    path resolve -- "$data"
    return 0
end

function __fishz_rows --argument-names data
    test -e "$data"; or return 0
    if not test -r "$data"
        printf 'fish-z: cannot read database: %s\n' "$data" >&2
        return 1
    end
    # A pipe or newline cannot be represented in the z database format.
    string match -r -- '^/[^|\r\n]*\|[0-9]+(?:\.[0-9]+)?\|[0-9]+$' <"$data"
    return 0
end

function __fishz_common
    set -l lengths (string length -- $argv)
    set -l minimum (math min (string join , -- $lengths))
    set -l i (contains -i -- "$minimum" $lengths)
    set -l shortest "$argv[$i]"
    test "$shortest" = /; and return 1
    set -l root (path normalize -- "$shortest")
    if test "$root" != /
        set -l prefix (string escape --style=regex -- "$root")
        string match -rvq -- "^$prefix(?:/|\$)" $argv; and return 1
    end
    printf '%s\n' "$shortest"
end
