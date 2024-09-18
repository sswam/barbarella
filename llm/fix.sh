#!/bin/bash -eu
# [prompt]
# Processes fixes in the input

apply_fixes() {
    local v=0    # verbosity level
    local m=     # model
    local p=     # extra prompt

    . opts

    local proc="proc"
    if [ "$v" = 1 ]; then
        proc="process"
    fi

    local prompt="Please fix this"
    if [ -n "$p" ]; then
        prompt+=", $p"
    fi

    $proc -m="$m" "$prompt"
}

if [ "$0" = "$BASH_SOURCE" ]; then
    apply_fixes "$@"
fi
