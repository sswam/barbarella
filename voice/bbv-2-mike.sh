#!/bin/bash -eu
# bb-voice: a simple voice chat program

set -a

. ./env.sh

nt mic

if [ ! -e "$file" ]; then
	> "$file"
fi

# rm -f /tmp/drop-the-mic

mic_on() { amixer sset Capture cap; }
mic_on

trap "mic_on; pkill -P $$" EXIT

mike.py | tee /dev/stderr | (
while read line; do
	if [ ! -s "$file" -a -n "$mission" ]; then
		echo >&2 1
		printf "%s\n%s: %s\n" "$mission" "$user" "$line" >> "$file"
	elif [ -n "$add_prompts" ]; then
		echo >&2 2
		printf "%s: %s\n" "$user" "$line" >> "$file"
	else
		echo >&2 3
		printf "%s\n" "$line" >> "$file"
	fi
	while read -t 0.1 line; do
		:
	done || true
done 
)
