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
    set -l case_mode smart
    test -n "$FISHZ_CASE"; and set case_mode "$FISHZ_CASE"
    set -l insensitive 0
    set -l smart 0
    if test "$case_mode" = ignore
        set insensitive 1
    else if test "$case_mode" = smart; or begin; test "$mode" = complete; and test "$FISHZ_COMPLETION" = legacy; end
        set smart 1
        if test "$pattern" = (string lower -- "$pattern")
            set insensitive 1
        end
    end

    set -l now (command date +%s)
    or return 1
    set -l rows (__fishz_rows "$data")
    or return 1
    set -q rows[1]; or return 1
    if test "$restrict" = 1
        set -l prefix (string escape --style=regex -- (path normalize -- "$PWD"))
        if test "$PWD" = /
            set rows (string match -r -- '^/[^|]+\|.*$' $rows)
        else
            set rows (string match -r -- "^$prefix/"'[^|]*\|.*$' $rows)
        end
    end
    # Match whole batches before doing any per-directory filesystem/scoring work.
    # The two final fields anchor the match inside the path, never its metadata.
    if test "$FISHZ_TRAILING_SLASH" = 1
        set rows (string replace -r '^(/[^|]+)\|' '$1/|' -- $rows)
    end
    set -l flags
    if test "$insensitive" = 1; or test "$smart" = 0
        set flags -i
    end
    set rows (string match -r $flags -- "^[^|]*(?:$regex)[^|]*\|[^|]*\|[^|]*\$" $rows)
    if test "$FISHZ_TRAILING_SLASH" = 1
        set rows (string replace -r '^(/[^|]+)/\|' '$1|' -- $rows)
    end
    set -q rows[1]; or return 1
    # A synthetic final component lets the stable native sort deduplicate by the
    # complete, literal path. The first duplicate still wins, including zero ranks.
    set rows (string replace '|' '|/' -- $rows | path sort -u --key=dirname | string replace '|/' '|')
    set -l scored (begin
        set -l candidate
        set -l frequency
        set -l stamp
        for line in $rows
            string match -rq '^(?<candidate>[^|]+)\|(?<frequency>[^|]+)\|(?<stamp>[^|]+)$' -- "$line"
            __fishz_keep "$candidate"; or continue
            set -l searchable "$candidate"
            if test "$FISHZ_TRAILING_SLASH" = 1; and test "$candidate" != /
                set searchable "$candidate/"
            end
            set -l bucket f
            if test "$insensitive" = 0; and string match -rq -- "$regex" "$searchable"
                set bucket e
            end
            set -l score
            set -l key
            switch "$method"
                case rank
                    set score "$frequency"
                    set key (math "floor($score * 100)")
                case time
                    set score (math "$stamp - $now")
                    set key "$stamp"
                case '*'
                    # Preserve the original six-decimal score and integer sort key.
                    set score (math "10000 * $frequency * 3.75 / (0.0001 * max(0, $now - $stamp) + 1.25)")
                    set key (math "floor($score * 100)")
            end
            if test "$mode" = list; and test "$score" = 0
                continue
            end
            printf '%s|%s|%s|%s\n' "$bucket" "$key" "$score" "$candidate"
        end
    end)
    set -l selected (string match 'e|*' -- $scored)
    set -l match_flags
    if not set -q selected[1]
        set selected (string match 'f|*' -- $scored)
        set match_flags -i
    end
    set -q selected[1]; or return 1
    set selected (string sub -s 3 -- $selected)

    # Rank the final nonempty term against the destination's basename. A term
    # containing slashes uses its last path component; the full ordered query
    # above still decides which paths qualify. Wildcards cannot cross a slash
    # when grading a basename, and trailing slashes do not change its name.
    set -l name_pattern ''
    for term in $terms
        test -n "$term"; and set name_pattern "$term"
    end
    set name_pattern (string trim -r -c / -- "$name_pattern")
    set name_pattern (string replace -r '^.*/' '' -- "$name_pattern")
    set name_pattern (string replace -ar '\s' '*' -- "$name_pattern")
    set selected (string replace -r '^' '1|' -- $selected)
    if test -n "$name_pattern"
        set -l name_regex (string escape --style=regex -- "$name_pattern")
        set name_regex (string replace -a '\\*' '[^/]*' -- "$name_regex")
        set name_regex (string replace -a '\\?' '[^/]' -- "$name_regex")
        # Upgrade path-only (1) to substring (2), prefix (3), then exact (4).
        # Batch replacements add the primary sort key without per-row subprocesses.
        set -l field '^[1-4]\|(?=[^|]*\|[^|]*\|.*/'
        set selected (string replace -r $match_flags -- "$field"'[^/]*'"(?:$name_regex)"'[^/]*/*$)' '2|' $selected)
        set selected (string replace -r $match_flags -- "$field(?:$name_regex)"'[^/]*/*$)' '3|' $selected)
        set selected (string replace -r $match_flags -- "$field(?:$name_regex)"'/*$)' '4|' $selected)
    end

    # path sort is fish's in-process natural sort. Integer keys preserve decimals.
    set -l direction -r
    if test "$mode" = list; and test "$method" != time
        set direction
    end
    set selected (path sort $direction -- $selected)
    set -l paths (string split -f 4 '|' -- $selected)
    set -l scores (string split -f 3 '|' -- $selected)
    if test "$mode" = complete
        if test "$FISHZ_COMPLETION" = legacy
            path sort -- $paths
        else
            printf '%s\n' $paths
        end
        return 0
    end
    if test "$mode" = list
        set -l common (__fishz_common $paths)
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
    end
    printf '%s\n' "$target"
end
