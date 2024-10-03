#!/bin/bash
# [program ...]
# Lint a program

. each

linty() {
	local verbose= v=0	# verbose mode, output results when all tests pass

	eval "$(ally)"

	if (( $# != 1 )); then
		each linty : "$@"
		return $?
	fi

	(
		local prog="$(finder "$1")"
		cd "$(dirname "$prog")"
		local ext="${prog##*.}"
		if [[ $prog != *.* ]]; then
			ext="sh"
		fi
		"lint_$ext" "$prog"
	)
}

run() {
	if (( verbose )); then
		v "$@"
	else
		v quiet "$@" 2>/dev/null
	fi
}

lint_sh() {
	local prog="$1"
	local fail=0
	run shfmt "$prog" || fail=1
	run shellcheck -x "$prog" || fail=1
	return $fail
}

lint_py() {
	local prog="$1"
	fail=0
	run python3 -m py_compile "$prog" || fail=1
	run pylint --disable=all --enable=fixme "$prog" || fail=1
	run mypy "$prog" || fail=1
	return $fail
}

lint_c() {
	local prog="$1"
	fail=0
	run gcc -Wall -Wextra -Werror -fsyntax-only "$prog" || fail=1
	run clang -Wall -Wextra -Werror -fsyntax-only "$prog" || fail=1
	run clang-tidy "$prog" || fail=1
	run cppcheck "$prog" || fail=1
	run splint "$prog" || fail=1
	run flawfinder "$prog" || fail=1
	return $fail
}

lint_pl() {
	local prog="$1"
	fail=0
	run perl -Mstrict -cw "$prog" || fail=1
	run perlcritic "$prog" || fail=1
	return $fail
}

lint_go() {
	local prog="$1"
	fail=0
	run go vet "$prog" || fail=1
	run golint "$prog" || fail=1
	run staticcheck "$prog" || fail=1
	return $fail
}

lint_rs() {
	local prog="$1"
	fail=0
	run rustc --deny warnings "$prog" || fail=1
	run cargo clippy --all-targets --all-features -- -D warnings || fail=1
	return $fail
}

lint_js() {
	local prog="$1"
	fail=0
	run eslint "$prog" || fail=1
	run jshint "$prog" || fail=1
	run standard "$prog" || fail=1
	return $fail
}

lint_ts() {
	local prog="$1"
	fail=0
	run tsc --noEmit "$prog" || fail=1
	lint_js "$prog" || fail=1
	return $fail
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
	linty "$@"
fi