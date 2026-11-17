# Source this file to load a checkout without installing it.
set -l root (path dirname -- (status filename))
if not contains -- "$root/functions" $fish_function_path
    set -p fish_function_path "$root/functions"
end
source "$root/conf.d/fish-z.fish"
