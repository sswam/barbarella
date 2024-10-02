#!/usr/bin/env bash

# [url]
# Fetches and summarizes web content

web_summary() {
	local name= n=	# name of the output file
	local dir= d="$ALLEMANDE_HOME/gen"	# directory to save the output
	local model= m=s	# model for the summary

	. opts

	# strict mode
	local old_opts=$(set +o)
	set -e -u -o pipefail
	trap 'eval "$old_opts"' RETURN

	# Support long and short options
	name=${name:-$n}
	dir=${dir:-$d}
	model=${model:-$m}

	# non-option arguments
	local url=${1:-}
	[ -n "$url" ] || usage "URL is required"

	if [ ! -d "$dir" ]; then
		echo >&2 "Error: Output directory does not exist: $dir"
		return 1
	fi

	if [ -z "$name" ]; then
		name=$(que -m="$model" "What's a short filename to document this resource, lower-case with .md extension: $url")
	fi

	web-text "$url" |
	proc "Please give a summary without any prelude, but with a heading reflecting the document." |
	v tee -a "$dir/$name"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
	web_summary "$@"
fi