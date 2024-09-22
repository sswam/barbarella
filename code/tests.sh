#!/bin/bash

# <program to test> "instructions to create tests" [reference files ...]
# Generate tests for a program using AI

tests() {
	local m=    # model
	local s=1   # refer to test_hello.py for test style

	. opts

	# strict mode
	local old_opts=$(set +o)
	set -e -u -o pipefail

	local program=$1
	local prompt=$2
	shift 2
	local refs=("$@")

	local dir=$(dirname "$program")
	local base=$(basename "$program")
	local stem=${base%.*}

	local ext=.${program##*.}
	if [ "$ext" == ".$base" ]; then
		ext=".sh"
	fi

	mkdir -p "$dir/tests"

	tests_ext=$ext

	executable=0
	case "$ext" in
	.sh)
		tests_ext=.bats
		executable=1
		if [ ! -e "$dir/tests/test_helper" ] && [ -d "/usr/lib/bats/bats-support" ]; then
			ln -s /usr/lib/bats "$dir/tests/test_helper"
		fi
	esac

	local tests_base="test_${stem}$tests_ext"
	local tests_path="$dir/tests/$tests_base"

	# Check if test file already exists
	if [ -e "$tests_path" ]; then
		echo >&2 "already exists: $tests_path"
		exit 1
	fi

	# Test style reference and prompt for -s option
	if [ "$s" = 1 ]; then
		local example="test_hello$tests_ext"
		refs+=("$example")
		prompt="in the style of \`$example\`, $prompt"
	fi

	prompt="Please write \`$tests_base\` to test \`$base\`, $prompt"

	local input=$(cat_named.py -p -b "$program" "${refs[@]}")

	if [ -z "$input" ]; then
		input=":)"
	fi

	# Process input and save result
	printf "%s\n" "$input" | process -m="$m" "$prompt" | markdown_code.py -c '#' > "$tests_path"

	if [ "$executable" = 1 ]; then
		chmod +x "$tests_path"
	fi

	vi -O "$tests_path" "$program"

	# restore caller options
	eval "$old_opts"
}

if [ "$BASH_SOURCE" = "$0" ]; then
	tests "$@"
fi
