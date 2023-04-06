#!/bin/bash -eu
# bb-voice: a simple voice chat program

set -a

. ./env.sh

nt speak

if [ ! -e "$file" ]; then
	> "$file"
fi

mic_on() { amixer sset Capture cap; }
mic_on

trap "mic_on; pkill -P $$" EXIT

tail -f -n"${rewind:-0}" "$file" |
perl -ne '
	chomp;
	BEGIN {
		$|=1;
		$last = "user";
	}
	s/[^ -~\x{7e3}]//g;    # filter out emojis; but \x7e9 is closing single-quote / "smart" apostrophe
	if (/^\Q$ENV{user}\E:/) {
		$last = "user";
	} elsif (/^\Q$ENV{bot}\E:/ || (!/^\w+: /) && $last eq "bot") {
		$last = "bot";
		print STDERR "$_\n";
		s/^\Q$ENV{bot}\E:\s*//;
		print("$_\n");
	} else {
		print STDERR "skipping line with user or unknown role: $_\n";
	}
' | $speak
