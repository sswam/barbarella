#!/bin/bash -eua
# bb-voice: a simple voice chat program

set -a

if [ ! -e "$file" ]; then
	> "$file"
fi

if [ -n "`amixer sget Capture | grep '\[off\]'`" ]; then
	mic_state=nocap
else
	mic_state=cap
fi

trap "amixer sset Capture $mic_state; pkill -P $$" EXIT

atail.py -f -r -n"${rewind:-0}" "$file" |
perl -ne '
	chomp;
	BEGIN {
		$|=1;
		$last = "user";
	}
	s/[^ -~\x{7e9}]//g;    # filter out emojis; but \x7e9 is closing single-quote / "smart" apostrophe
	if (/^$/) {
		$last = "";
	} elsif (/^\Q$ENV{user}\E:/) {
		$last = "user";
	} elsif (/^\Q$ENV{bot}\E:/ || (!/^\w+:\s/) && $last eq "bot") {
		$last = "bot";
		print STDERR "$_\n";
		s/^\Q$ENV{bot}\E:\s*//;
		print("$_\n");
	} else {
		print STDERR "skipping line with user or unknown role: $_\n";
	}
' | $speak
