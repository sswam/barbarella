#!/usr/bin/make -f

img_rate=1

# threads=$(shell nproc)

MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
export PATH := $(MAKEFILE_DIR):$(PATH)


SHELL := /bin/bash
WHISPER := whisper
WHISPER_MODEL := large
SEARCH := google

# WHISPER := whisp
# WHISPER_MODEL := models/ggml-large.bin


# m0=3+
m0=3+
m=4


default: goal

clean: cleanish
	rm *.webm *.txt

cleanish:
	mv web-address.txt web-address.txt.bak || true
	rm *.txt *.html *.md *.tsv *.json *.txt *.vtt *.srt *.prompt
	mv web-address.txt.bak web-address.txt || true

transcript.sent.txt: transcript.txt
	< $< split_sentences > $@

transcript.sent2.txt: transcript.sent.txt
	< $< ai_split_long_sentences.py > $@

web-address.txt:
	if [ -n "$(url)" ]; then \
		echo "$(url)" >$@; \
		else read -p "Enter URL: " url; \
		echo $$url >$@; \
	fi

video.webm: web-address.txt
	yt-dlp -q -f bestvideo -o "$@" "`<$<`"
	if [ ! -e "$@" ]; then mv -i "$@".* "$@"; fi
	if [ -e "$@" ]; then touch $@; fi

audio.webm: web-address.txt
	yt-dlp -q -f bestaudio -o "$@" "`<$<`"
	if [ ! -e "$@" ]; then mv -i "$@".* "$@"; fi
	if [ -e "$@" ]; then touch $@; fi

audio.wav: audio.webm
	ffmpeg -loglevel error -i $< -vn -acodec pcm_s16le -ac 1 -ar 16000 $@

av.webm: video.webm audio.webm
	ffmpeg -loglevel error -i video.webm -i audio.webm -c copy $@
	if [ ! -e "$@" ]; then mv -i "$@".* "$@"; fi

title.txt: web-address.txt
	web-title "`<web-address.txt`" >$@

title-clean.txt: title.txt
	< $< perl -pe 's/- YouTube$$//; s/\(.*?\)//g; s/\[.*?\]//g; s/\{.*?\}//g;' > $@

# get images from the video, one every $img_rate seconds
images: video.webm
	mkdir -p images
	ffmpeg -loglevel error -i $< -vf fps=1/$(img_rate) -qscale:v 2 images/%06d.jpeg

audio-extract: av
	ffmpeg -loglevel error -i $< -vn -c copy $@

audio.txt: audio.wav
	$(WHISPER) --language en --model $(WHISPER_MODEL) $$PWD/$<

audio-clean.txt: audio.txt
	< $< tr -d '♪' | strip-lines.py | squeeze-blank-lines.pl 1 > $@

summary.txt: transcript.txt
	< $< gpt-summary -m="$m" > $@

name.txt: transcript.txt title-clean.txt
	if [ -n "$(name)" ] ; then \
		echo "$(name)" > $@ ; \
	else \
		< $< gpt process -m "$m" "Please respond with a short name for this article / video transcript. The given title was `<title-clean.txt`:" --prompt2 "Respond with just a short name for the above article." > $@ ; \
	fi

topic.txt: transcript.txt
	< $< gpt-topic -m="$m" > $@

flashcards-1.txt: transcript.txt
	< $< gpt-flashcards -m="$m" > $@

flashcards.txt: flashcards-1.txt
	(< $< grep -v '^$$' | sed 's/^Prompt:/\n&/' | sed '1{/^$$/d}'; echo) | single-blank-lines.pl > $@

flashcards.tsv: flashcards.txt
	< $< recs2tsv.pl | grep '\S' > $@

correct.prompt:
	ln -s `wich correct.prompt` .

prompt-transcript.txt: audio-clean.txt correct.prompt
	CONTENT=`< $<` shell-template.sh correct.prompt > $@

transcript.txt: prompt-transcript.txt title-clean.txt
	< $< gpt process -m "$(m0)" "Please reply with just the corrected transcript. The proper title of the video is `<title-clean.txt`" > $@

transcript.md: transcript.txt
	< $< nl | (echo "| n | line |"; sed 's/^ *//') | tsv2markdown.sh >$@


# We could also search to find the title or canonical page.

search-lyrics-query.txt: name.txt title-clean.txt
	echo "`< title-clean.txt` lyrics or transcript" > $@

search-lyrics.txt: search-lyrics-query.txt
	search -e $(SEARCH) "`< search-lyrics-query.txt`" >$@

lyrics-url.txt: search-lyrics.txt name.txt
	< $< gpt process -m "$m" "Please reply with just the best URL to get lyrics or a transcript for `<name.txt`, based on these search results or your knowledge. If nothing looks promising, just reply 'about:blank'." > $@

lyrics.html: lyrics-url.txt
	wg "`< $<`" -O- >$@ || true

lyrics-page.txt: lyrics.html
	w3m -dump $< > $@ || true

extract.prompt:
	ln -s `wich extract.prompt`

prompt-lyrics.txt: lyrics-page.txt extract.prompt
	if [ ! -s $< ]; then \
		echo "No lyrics found." ; > $@ ; \
	else \
		CONTENT=`< $<` shell-template.sh extract.prompt > $@ ; \
	fi

lyrics.txt: prompt-lyrics.txt name.txt
	if [ ! -s $< ]; then \
		echo "No lyrics found." ; > $@ ; \
	else \
		< $< gpt process -m "$m" "Please reply with just the lyrics or transcript for `<name.txt`, based on the page `<lyrics-url.txt`." > $@ ; \
	fi

post.txt: title.txt web-address.txt name.txt topic.txt summary.txt flashcards.txt transcript.txt # lyrics.txt
	cat-sections.py $^ > $@

%.words.txt: %.txt
	< $< words-split.py > $@

diff: transcript.words.txt audio-clean.words.txt lyrics.words.txt 
	vimdiff $^

goal: post.txt flashcards.tsv # images


.PRECIOUS:
.VIRTUAL: default
