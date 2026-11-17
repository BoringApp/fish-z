function __fishz_query --argument-names data mode method restrict
    __fishz_util
    set -l terms $argv[5..]
    set -l pattern (string join ' ' -- $terms)
    set pattern (string replace -ar '\s' '*' -- "$pattern")
    # Compile the small, documented wildcard language ourselves. In fish 4,
    # string match's glob '?' otherwise depends on the qmark-noglob feature.
    set -l regex (string escape --style=regex -- "$pattern")
    set regex (string replace -a '\\*' '.*' -- "$regex")
    set regex (string replace -a '\\?' '.' -- "$regex")
    set -l insensitive 0
    set -l smart 0
    if test "$FISHZ_CASE" = ignore
        set insensitive 1
    else if test "$FISHZ_CASE" = smart; or begin; test "$mode" = complete; and test "$FISHZ_COMPLETION" = legacy; end
        set smart 1
        if test "$pattern" = (string lower -- "$pattern")
            set insensitive 1
        end
    end

    set -l now (command date +%s)
    or return 1
    set -l rows (__fishz_rows "$data")
    or return 1
    set -l exact
    set -l folded
    set -l seen
    for line in $rows
        set -l parts (string split '|' -- "$line")
        set -l candidate "$parts[1]"
        contains -- "$candidate" $seen; and continue
        set -a seen "$candidate"
        __fishz_keep "$candidate"; or continue
        if test "$restrict" = 1
            __fishz_under "$candidate" "$PWD"; or continue
            test "$candidate" = "$PWD"; and continue
        end
        set -l searchable "$candidate"
        if test "$FISHZ_TRAILING_SLASH" = 1; and test "$candidate" != /
            set searchable "$candidate/"
        end
        set -l bucket
        if test "$insensitive" = 1
            string match -irq -- "$regex" "$searchable"; or continue
            set bucket folded
        else if string match -rq -- "$regex" "$searchable"
            set bucket exact
        else if test "$smart" = 0; and string match -irq -- "$regex" "$searchable"
            set bucket folded
        else
            continue
        end
        set -l score
        set -l key
        switch "$method"
            case rank
                set score "$parts[2]"
                set key (math "floor($score * 100)")
            case time
                set score (math "$parts[3] - $now")
                set key "$parts[3]"
            case '*'
                # zsh-z 2.0.1 frecency; clamp future timestamps after clock changes.
                set score (math "10000 * $parts[2] * 3.75 / (0.0001 * max(0, $now - $parts[3]) + 1.25)")
                set key (math "floor($score * 100)")
        end
        if test "$mode" = list; and test "$score" = 0
            continue
        end
        set -a $bucket "$key|$score|$candidate"
    end
    set -l selected $exact
    set -l match_flags
    if not set -q selected[1]
        set selected $folded
        set match_flags -i
    end
    set -q selected[1]; or return 1

    # path sort is fish's in-process natural sort. Integer keys preserve decimals.
    set -l direction -r
    if test "$mode" = list; and test "$method" != time
        set direction
    end
    set selected (path sort $direction -- $selected)
    set -l paths
    set -l scores
    for line in $selected
        set -l parts (string split -m 2 '|' -- "$line")
        set -a scores "$parts[2]"
        set -a paths "$parts[3]"
    end
    if test "$mode" = complete
        if test "$FISHZ_COMPLETION" = legacy
            path sort -- $paths
        else
            printf '%s\n' $paths
        end
        return 0
    end
    set -l common (__fishz_common $paths)
    if test "$mode" = list
        if set -q common[1]; and test (count $paths) -gt 1
            printf '%-10s %s\n' common: (__fishz_display "$common")
        end
        set -l i 0
        for candidate in $paths
            set i (math "$i + 1")
            printf '%-10s %s\n' (string replace -r '\..*$' '' -- "$scores[$i]") (__fishz_display "$candidate")
        end
        return 0
    end
    set -l target "$paths[1]"
    if test "$FISHZ_UNCOMMON" = 1; and test -n "$pattern"
        # Keep the deepest occurrence of the query; trim only irrelevant suffixes.
        # Compare matched character counts, as upstream does, so ordered terms,
        # wildcard queries, and repeated occurrences all retain their meaning.
        set -l trim_regex (string replace -r '/$' '' -- "$regex")
        set -l remainder (string replace $match_flags -ra -- "$trim_regex" '' "$target")
        set -l matched_length (math (string length -- "$target") - (string length -- "$remainder"))
        set -l parent (path dirname -- "$target")
        while test "$parent" != "$target"
            set remainder (string replace $match_flags -ra -- "$trim_regex" '' "$parent")
            set -l parent_length (math (string length -- "$parent") - (string length -- "$remainder"))
            test "$parent_length" -eq "$matched_length"; or break
            set target "$parent"
            set parent (path dirname -- "$target")
        end
    else if set -q common[1]
        set target "$common"
    end
    printf '%s\n' "$target"
end
