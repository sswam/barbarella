#!/usr/bin/env bash
#
# [options] [prompt ...]
# Process input text using an LLM, and reply concisely

proc() {
	local model= m=
	local empty_ok=	e=	# empty input is okay

	eval "$(ally)"

	local prompt="$*"

	opts=""
	if [ "$empty_ok" = 1 ]; then
		opts="--empty-ok"
	fi

	process -m="$model" $opts "$prompt" "Please reply as concise as possible, with no boilerplate \
	or unnecessary explanation. Do not abbreviate text unrelated to the request. \
	If editing, do not make edits that are not requested (e.g. removing comments \
	or blank lines). If the input has code but does not include code quoting with \
	\`\`\`, the output should not include \`\`\` either. If writing code, be \
	concise but clear, not obscure.
	$*" | rstrip
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
	process "$@"
fi

# version: 1.0.1
