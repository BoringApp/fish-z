# fish-z settings use FISHZ_ exclusively; no jethrokuan/z compatibility layer.
if not status is-interactive
    return
end
set -l cmd z
set -q FISHZ_CMD[1]; and set cmd "$FISHZ_CMD"
if not string match -rq '^[a-zA-Z_][a-zA-Z0-9_-]*$' -- "$cmd"
    printf 'fish-z: invalid FISHZ_CMD\n' >&2
    return 1
end
if test "$cmd" != fishz
    function $cmd --description 'Jump to a frequently or recently visited directory'
        fishz $argv
    end
end
complete -c "$cmd" -e
complete -c "$cmd" -f -k -a '(__fishz_complete)'
complete -c "$cmd" -s c -d 'Only descendants of the current directory'
complete -c "$cmd" -s e -d 'Print the best match'
complete -c "$cmd" -s l -d 'List matches and scores'
complete -c "$cmd" -s r -d 'Match by frequency'
complete -c "$cmd" -s t -d 'Match by recency'
complete -c "$cmd" -s x -d 'Forget a directory'
complete -c "$cmd" -s R -d 'With -x, forget the entire subtree'
complete -c "$cmd" -s h -l help -d 'Show help'
complete -c "$cmd" -l add -d 'Record a visit explicitly'

function __fishz_chpwd --on-variable PWD
    set -e __fishz_removed_pwd
end
function __fishz_prompt --on-event fish_prompt
    __fishz_util
    test "$fish_private_mode" = 1; and return
    test "$__fishz_removed_pwd" = "$PWD"; and return
    test "$PWD" = "$HOME"; and return
    # Avoid stacking workers in a single shell during rapid prompt redraws.
    if set -q __fishz_writer_pid[1]; and command kill -0 $__fishz_writer_pid 2>/dev/null
        return
    end
    set -l data (__fishz_data 2>/dev/null)
    or return
    set -l target (__fishz_path "$PWD")
    __fishz_record add "$target" "$data" 1
end
