function __fishz_complete
    set -l tokens (commandline -opc)
    set -e tokens[1]
    set -l current (commandline -ct)
    set current (string unescape -n -- "$current" 2>/dev/null; or printf '%s\n' "$current")
    fishz --complete $tokens "$current" 2>/dev/null | while read -l candidate
        # Fish escapes the insertion itself. Tabs delimit completion descriptions.
        string match -rq '\t' -- "$candidate"; and continue
        printf '%s\tvisited directory\n' "$candidate"
    end
end
