# Runs only in an isolated fish process. All mutations share one transaction.
function __fishz_write
    __fishz_util
    argparse 'data=' 'timeout=' 'max-score=' 'keep=+' -- $argv
    or return 2
    set -g FISHZ_KEEP_DIRS $_flag_keep
    set -l data "$_flag_data"
    set -l action "$argv[1]"
    set -l target "$argv[2]"
    if not string match -rq '^[0-9]+(\.[0-9]+)?$' -- "$_flag_timeout" "$_flag_max_score"
        printf 'fish-z: timeout and max score must be nonnegative numbers\n' >&2
        return 1
    end
    # Explicitly validate both; string match succeeds if either argument matches.
    for number in "$_flag_timeout" "$_flag_max_score"
        string match -rq '^[0-9]+(\.[0-9]+)?$' -- "$number"; or return 1
    end
    if string match -rq '[|\r\n]' -- "$target"
        printf 'fish-z: paths containing pipes or newlines cannot be recorded\n' >&2
        return 1
    end
    set -l directory (path dirname -- "$data")
    # This worker owns its umask; the calling interactive shell is unaffected.
    umask 077
    command mkdir -p -- "$directory"; or return 1
    set -g __fishz_lock "$data.lock.d"
    set -g __fishz_held 0
    set -g __fishz_temp
    set -g __fishz_cancel 0
    function __fishz_release --on-event fish_exit
        if set -q __fishz_temp[1]
            command rm -f -- "$__fishz_temp"
        end
        if test "$__fishz_held" = 1
            command rm -f -- "$__fishz_lock/owner"
            command rmdir -- "$__fishz_lock"
        end
    end
    function __fishz_terminate --on-signal TERM
        set -g __fishz_cancel 143
    end
    function __fishz_interrupt --on-signal INT
        set -g __fishz_cancel 130
    end
    function __fishz_hangup --on-signal HUP
        set -g __fishz_cancel 129
    end
    set -l attempts (math "ceil($_flag_timeout / 0.02)")
    set -l attempt 0
    while not command mkdir -- "$__fishz_lock" 2>/dev/null
        test "$__fishz_cancel" -ne 0; and return $__fishz_cancel
        if test "$attempt" -ge "$attempts"
            printf 'fish-z: database lock timed out: %s\n' "$__fishz_lock" >&2
            return 2
        end
        sleep 0.02
        set attempt (math "$attempt + 1")
    end
    set -g __fishz_held 1
    # Signal handlers only mark cancellation. In particular, do not exit between
    # a successful mkdir and recording ownership: that would strand the lock.
    test "$__fishz_cancel" -ne 0; and return $__fishz_cancel
    printf '%s\n' "$fish_pid" >"$__fishz_lock/owner"; or return 1

    set -l rows (__fishz_rows "$data")
    or return 1
    set -l paths
    set -l ranks
    set -l times
    set -l total 0
    set -l removed 0
    for line in $rows
        test "$__fishz_cancel" -ne 0; and return $__fishz_cancel
        set -l parts (string split '|' -- "$line")
        if test "$action" != add
            if test "$parts[1]" = "$target"; or begin; test "$action" = remove-tree; and __fishz_under "$parts[1]" "$target"; end
                set removed 1
                continue
            end
        else
            __fishz_keep "$parts[1]"; or continue
            test "$parts[2]" -ge 1; or continue
        end
        set -l i (contains -i -- "$parts[1]" $paths)
        if test -z "$i"
            set -a paths "$parts[1]"
            set -a ranks "$parts[2]"
            set -a times "$parts[3]"
        else
            set ranks[$i] "$parts[2]"
            set times[$i] "$parts[3]"
        end
    end
    if test "$action" = add
        set -l now (command date +%s)
        or return 1
        for rank in $ranks
            set total (math "$total + $rank")
        end
        set -l i (contains -i -- "$target" $paths)
        if test -n "$i"
            set ranks[$i] (math "$ranks[$i] + 1")
            set times[$i] "$now"
        else
            set -a paths "$target"
            set -a ranks 1
            set -a times "$now"
        end
        if test "$total" -gt "$_flag_max_score"
            set -l aged
            for rank in $ranks
                set -a aged (math "$rank * 0.99")
            end
            set ranks $aged
        end
    else if test "$removed" = 0
        return 1
    end

    set -g __fishz_temp (command mktemp "$data.XXXXXXXX")
    or return 1
    begin
        set -l i 0
        for entry in $paths
            test "$__fishz_cancel" -ne 0; and return $__fishz_cancel
            set i (math "$i + 1")
            printf '%s|%s|%s\n' "$entry" "$ranks[$i]" "$times[$i]"
            or return 1
        end
    end >"$__fishz_temp"
    or return 1
    test "$__fishz_cancel" -ne 0; and return $__fishz_cancel
    command chmod 600 "$__fishz_temp"; or return 1
    command mv -f -- "$__fishz_temp" "$data"
    or return 1
    set -e __fishz_temp
    return $__fishz_cancel
end
