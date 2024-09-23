#!/bin/bash
# [prog.py] "instructions to improve it" [reference files ...]
# Improve a program using AI
set -e -u -o pipefail

improve() {
	local m=	# model
	local s=0	# refer to hello.<ext> for code style
	local E=0	# do not edit
	local c=0	# concise

	. opts

	local prog=$1
	local prompt=$2
	shift 2 || true
	local refs=("$@")

	# Check if program exists
	if [ ! -e "$prog" ]; then
		local prog2=`wich $prog`
		if [ ! -e "$prog2" ]; then
			echo >&2 "not found: $prog"
			exit 1
		fi
		prog=$prog2
	fi

	# resolve symlinks
	prog=$(readlink -f "$prog")

	local base=$(basename "$prog")
	local ext=${base##*.}
	if [ "$ext" == "$base" ]; then
		ext="sh"
	fi

	# Code style reference and prompt for -s option
	if [ "$s" = 1 ]; then
		refs+=("hello_$ext.$ext")
		prompt="in the style of \`hello_$ext.$ext\`, $prompt"
	fi

	prompt="Please improve \`$base\`, you can bump the patch version, $prompt"

	if [ "$c" = 1 ]; then
		prompt="$prompt, Please reply concisely with only the changed code, not the whole program."
	fi

	local input=$(cat_named.py -p -b "$prog" "${refs[@]}")

	# Backup original file
	if [ -e "$prog~" ]; then
		move-rubbish "$prog~"
	fi
	echo n | cp -i -a "$prog" "$prog~"   # WTF, there's no proper no-clobber option?!

	# Process input and save result
	printf "%s\n" "$input" | process -m="$m" "$prompt" | markdown_code.py -c '#' > "$prog~"
	swapfiles "$prog" "$prog~"

	# Compare original and improved versions
	if [ "$E" = 0 ]; then
		vimdiff "$prog" "$prog~"
	fi
}

if [ "$BASH_SOURCE" = "$0" ]; then
	improve "$@"
fi
