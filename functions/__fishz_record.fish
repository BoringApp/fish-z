function __fishz_record --argument-names action target data background
    __fishz_util
    if test "$action" = add
        set -q fish_private_mode; and test "$fish_private_mode" = 1; and return 0
        test -d "$target"; or return 1
        test "$target" = "$HOME"; and return 0
        for root in $FISHZ_EXCLUDE_DIRS
            __fishz_under "$target" "$root"; and return 0
        end
    end
    set -l timeout 1
    set -q FISHZ_LOCK_TIMEOUT[1]; and set timeout "$FISHZ_LOCK_TIMEOUT"
    set -l max_score 9000
    set -q FISHZ_MAX_SCORE[1]; and set max_score "$FISHZ_MAX_SCORE"
    set -l options --data "$data" --timeout "$timeout" --max-score "$max_score"
    for root in $FISHZ_KEEP_DIRS
        set -a options --keep "$root"
    end
    # The child has no startup config, so it cannot recursively load prompt hooks.
    set -l library (path dirname -- (status filename))
    set -l runner 'set -p fish_function_path $argv[1]; __fishz_write $argv[2..]'
    set -l fish_binary (status fish-path)
    if test "$background" = 1
        command "$fish_binary" --no-config -c "$runner" "$library" $options -- "$action" "$target" </dev/null >/dev/null 2>&1 &
        set -g __fishz_writer_pid $last_pid
        disown $last_pid 2>/dev/null
    else
        # Serialize this shell's queued add before a foreground removal, otherwise
        # an older background job could re-add the entry after z -x returns.
        if set -q __fishz_writer_pid[1]
            set -l remaining (math "ceil($timeout / 0.02)")
            while command kill -0 $__fishz_writer_pid 2>/dev/null
                if test "$remaining" -le 0
                    printf 'fish-z: previous background write has not finished\n' >&2
                    return 2
                end
                sleep 0.02
                set remaining (math "$remaining - 1")
            end
            set -e __fishz_writer_pid
        end
        command "$fish_binary" --no-config -c "$runner" "$library" $options -- "$action" "$target"
    end
end
