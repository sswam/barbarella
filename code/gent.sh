#!/bin/bash

# <program to test> "instructions to create tests" [reference files ...]
# Generate tests for a program using AI

gent() {
	local model= m=   # model
	local style= s=1  # refer to test_hello.py for test style
	local edit= e=1   # do not edit
	local test= t=1	  # run tests after generating

	eval "$(ally)"

	local program=$1
	local prompt=${2:-}
	shift 2 || shift 1 || true
	local refs=("$@")

	if [ ! -e "$program" ]; then
		program=$(readlink -f "$(which-file "$program")")
	fi

	local dir=$(dirname "$program")
	local base=$(basename "$program")
	local stem=${base%.*}

	local ext=${base##*.}
	if [ "$ext" == "$base" ]; then
		ext="sh"
	fi

	tests_ext=$ext
	tests_dir=$dir/tests

	executable=0
	case "$ext" in
	sh)
		tests_ext=bats
		executable=1
		if [ ! -e "$dir/tests/test_helper" ] && [ -d "/usr/lib/bats/bats-support" ]; then
			ln -s /usr/lib/bats "$dir/tests/test_helper"
		fi
		;;
	go)
		tests_dir=$dir
		;;
	esac

	local tests_base="${stem}_test.$tests_ext"
	local tests_path="$tests_dir/$tests_base"

	mkdir -p "$(dirname "$tests_path")"

	# Check if test file already exists
	if [ -s "$tests_path" ]; then
		echo >&2 "already exists: $tests_path"
		exec improve "$tests_path" "Please improve the tests, fixing and adding test cases as needed." "$program" "${refs[@]}"
		exit 1
	fi

	# Test style reference and prompt for -s option
	style_ref="$ALLEMANDE_HOME/$ext/tests/hello_${ext}_test.$tests_ext"
	if ((style)) && [ -e "$style_ref" ]; then
		refs+=("$style_ref")
		prompt="in the style of \`$style_ref\`, $prompt"
	fi

	prompt="Please write \`$tests_base\` to test \`$base\`, $prompt"

	local input=$(cat-named -p -b "$program" "${refs[@]}")

	if [ -z "$input" ]; then
		input=":)"
	fi

	# Process input and save result
	printf "%s\n" "$input" | process -m="$model" "$prompt" | markdown-code -c '#' > "$tests_path"

	if [ "$executable" = 1 ]; then
		chmod +x "$tests_path"
	fi

	if ((edit)); then
		$EDITOR -O "$tests_path" "$program"
	fi

	if ((test)); then
		testy "$program"
	fi
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
	gent "$@"
fi
