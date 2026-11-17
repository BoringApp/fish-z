# fish-native behavioral port of agkozak/zsh-z v2.0.1. See LICENSE.
function fishz --description 'Jump to a frequently or recently visited directory'
    __fishz_util
    argparse -n fish-z --exclusive r,t h/help c e l r t x R add complete -- $argv
    or return 2
    if set -q _flag_help; and not set -q _flag_complete
        printf '%s\n' 'Usage: z [-celrt] [pattern ...]' \
            '       z --add path | z -x[R] [path]' \
            '  no arguments  list visited directories' \
            '  -c            restrict to descendants of the current directory' \
            '  -e            print the best match without changing directory' \
            '  -l            list matches and their scores' \
            '  -r / -t       rank by frequency / recency' \
            '  -x / -xR      forget a directory / its entire subtree' \
            '  --add         record a visit explicitly' \
            '  --            end options (for patterns beginning with -)'
        return 0
    end
    if set -q _flag_R; and not set -q _flag_x; and not set -q _flag_complete
        printf 'fish-z: -R requires -x\n' >&2
        return 2
    end
    if set -q _flag_add; and set -q _flag_x; and not set -q _flag_complete
        printf 'fish-z: --add and -x cannot be combined\n' >&2
        return 2
    end
    set -l data (__fishz_data)
    or return 1
    if not set -q _flag_complete
        if set -q _flag_add; or set -q _flag_x
            if test (count $argv) -gt 1
                printf 'fish-z: quote paths containing spaces\n' >&2
                return 2
            end
            set -l target "$argv[1]"
            if test -z "$target"
                set -q _flag_add; and return 2
                set target "$PWD"
            end
            set -l action add
            set -q _flag_x; and set action remove
            set -q _flag_R; and set action remove-tree
            set target (__fishz_path "$target")
            if test "$action" = remove-tree; and test "$target" = /
                read -l -P 'Delete the entire fish-z history? [y/N] ' answer
                contains -- "$answer" y Y yes; or return 1
            end
            __fishz_record "$action" "$target" "$data"
            set -l result $status
            if test "$result" = 0; and set -q _flag_x
                set -g __fishz_removed_pwd "$PWD"
            end
            return $result
        end
    end
    set -l mode jump
    set -q _flag_l; and set mode list
    test (count $argv) = 0; and set mode list
    set -q _flag_complete; and set mode complete
    set -l method frecent
    set -q _flag_r; and set method rank
    set -q _flag_t; and set method time
    set -l restrict 0
    set -q _flag_c; and set restrict 1
    set -l target
    # A selected absolute completion is a destination, even after several terms.
    if test "$mode" = jump; and not set -q _flag_e; and set -q argv[-1]
        if string match -q '/*' -- "$argv[-1]"; and test -d "$argv[-1]"
            set target "$argv[-1]"
        end
    end
    if test "$mode" != jump
        __fishz_query "$data" "$mode" "$method" "$restrict" $argv
        return $status
    end
    if not set -q target[1]
        set target (__fishz_query "$data" "$mode" "$method" "$restrict" $argv)
        if test $status != 0
            set -l requested (string join ' ' -- $argv)
            if not set -q _flag_e; and test -d "$requested"
                set target "$requested"
            else
                return 1
            end
        end
    end
    if set -q _flag_e
        __fishz_display "$target"
        return 0
    end
    if set -q FISHZ_CD[1]
        $FISHZ_CD "$target"
    else
        builtin cd -- "$target"
    end
    or return $status
    test "$FISHZ_ECHO" = 1; and __fishz_display "$PWD"
    return 0
end
