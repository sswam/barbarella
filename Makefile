export

SHELL := /bin/bash

WEBCHAT := $(ALLYCHAT_HOME)
ROOMS := $(ALLEMANDE_ROOMS)
WATCH_LOG := $(ALLEMANDE_HOME)/watch.log
SCREEN := $(ALLEMANDE_SCREEN)
SCREENRC := $(ALLEMANDE_HOME)/config/screenrc
TEMPLATES := $(WEBCHAT)/templates
SUBDIRS := $(dir $(wildcard */Makefile))

JOBS := server_start server_stop beorn server default run-i3 run frontend backend dev \
	run core vi-online vi-local vscode-online vscode-local voice webchat llm whisper chat-api stream auth watch \
	bb2html nginx logs perms brain mike speak \
	firefox-webchat-online firefox-webchat-local firefox-pro-local firefox-pro-online \
	chrome-webchat-online chrome-webchat-local \
	stop mount umount fresh \
	install install-dev uninstall clean i3-layout

all: api_doc subdirs canon

deps:: deb-deps
deps:: venv

deb-deps: deps-allemande_0.1_all.deb

deps-allemande_0.1_all.deb: debian-packages.txt
	env -i PATH=$$PATH HOME=$$HOME metadeb -n=deps-allemande debian-packages.txt

venv: requirements.txt
	[ -e venv ] || python -m venv venv
	. venv/bin/activate; pip install -r requirements.txt
	touch venv

subdirs: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) -C $@

server_start:
	ssh -t $(SERVER_SSH) "cd $(ALLEMANDE_HOME) && . ./env.sh && make server"

server_stop:
	ssh -t $(SERVER_SSH) "cd $(ALLEMANDE_HOME) && . ./env.sh && make stop"

beorn: clean run-i3-screen mount
i3: connect-i3-screen

server:: stop
server:: clean
server:: webchat brain.xt

run-i3-screen:: i3-layout
run-i3-screen:: stop
run-i3-screen:: run

connect-i3-screen:: i3-layout
connect-i3-screen:: connect

run: frontend backend dev flash.xt alfred.xt opal-loop.xt
# vi-online.xt
# pro-dev 
connect: frontend backend.xtc dev.xtc pro-dev.xtc flash.xtc alfred.xtc vi-online.xtc
disconnect:
	psgrep 'xterm -e screen -x [a]llemande -p ' | k 2 | xa kill

frontend: firefox-webchat-online vi-online.xt
# firefox-pro-online chrome-webchat-online
frontend-local: vscode-local firefox-webchat-local firefox-pro-local chrome-webchat-local

backend: core webchat
# voice
backend.xtc: core.xtc webchat.xtc
# voice.xtc 

dev: clean nginx.xt logs.xt
dev.xtc: clean nginx.xtc logs.xtc

install:
	allemande-install
	allemande-user-add www-data
	web-install

install-dev:
	allemande-install
	allemande-user-add $$USER
	web-install

uninstall:
	allemande-uninstall
	web-uninstall

core: llm.xt a1111.xt # whisper.xt

voice: mike.xt speak.xt whisper.xt

webchat: chat-api.xt stream.xt watch.xt bb2html.xt auth.xt

pro: svelte.xt
pro-dev: svelte-dev.xt

svelte:
	cd $(ALLEMANDE_HOME)/pro && npm run build
	cd $(ALLEMANDE_HOME)/pro && node build

svelte-dev:
	cd $(ALLEMANDE_HOME)/pro && npm run dev

flash:
	cd $(ALLEMANDE_HOME)/apps/flash && \
	./flash-webui.py

alfred:
	cd $(ALLEMANDE_HOME)/apps/alfred && \
	./alfred-webui.py

core.xtc: llm.xtc a1111.xtx # whisper.xtc

voice.xtc: mike.xtc speak.xtc  # brain.xtc

webchat.xtc: chat-api.xtc stream.xtc watch.xtc bb2html.xtc auth.xtc

pro.xtc: svelte.xtc
pro-dev.xtc: svelte-dev.xtc

clean:
	spool-cleanup
	spool-history-rm
	> watch.log

llm:
	while true; do $(PYTHON) core/llm_llama.py -m "$(LLM_MODEL)" -d; sleep 1; done

whisper:
	sudo -E -u $(ALLEMANDE_USER) $(PYTHON) core/stt_whisper.py -d

a1111:
	$(PYTHON) core/image_a1111.py -d

# brain-remote: clean
# 	cd chat && ./brain.sh --remote

brain: clean
	cd chat && ./brain.sh

# brain-local: clean
# 	cd chat && ./brain.sh --local

mike:
	cd voice-chat && ./bb_mike.sh

speak:
	cd voice-chat && ./bb_speak.sh

vi-online:
	ssh -t $(SERVER_SSH) 'cd $(ALLEMANDE_HOME) && vi -p "$$file"'

vi-local:
	vi -p "$$file"

vscode-online:
	code "$$file_server" & disown

vscode-local:
	code "$$file" & disown

chat-api:
	cd $(WEBCHAT) && uvicorn chat-api:app --reload --timeout-graceful-shutdown 5 # --reload-include *.csv

stream:
	cd $(WEBCHAT) && uvicorn stream:app --reload --port 8001 --timeout-graceful-shutdown 1

auth:
	cd auth && uvicorn auth:app --reload --timeout-graceful-shutdown 5 --port 8002

watch:
	awatch -r -A -x bb -p $(ROOMS) >> $(WATCH_LOG)

bb2html:
	$(WEBCHAT)/bb2html.py -w $(WATCH_LOG)

nginx:
	(echo; inotifywait -q -m -e modify $(ALLEMANDE_HOME)/adm/nginx ) | while read e; do v restart-nginx; echo ... done; done

logs:
	tail -f /var/log/nginx/access.log /var/log/nginx/error.log

firefox-webchat-local:
	(sleep 1; firefox -P "$$USER" "https://chat-local.allemande.ai/#$$room") & disown

firefox-webchat-online:
	(sleep 1; firefox -P "$$USER" "https://chat.allemande.ai/#$$room") & disown

firefox-pro-local:
	(sleep 1; firefox -P "$$USER" "https://pro-local.allemande.ai/") & disown

firefox-pro-online:
	(sleep 1; firefox -P "$$USER" "https://pro.allemande.ai/") & disown

chrome-webchat-local:
	(sleep 1; chrome "https://chat-local.allemande.ai/#$$room") & disown

chrome-webchat-online:
	(sleep 1; chrome "https://chat.allemande.ai/#$$room") & disown

%.xt:
	xterm-screen-run "$(SCREEN)" "$*" nt-make "$*"; sleep 0.1

%.xtc:
	xterm-screen-connect "$(SCREEN)" "$*"

i3-layout:
	if [ -n "$$DISPLAY" ] && which i3-msg; then i3-msg "append_layout $(ALLEMANDE_HOME)/i3/layout.json"; fi

stop:
	screen -S "$(SCREEN)" -X quit || true

mount:
	ally-mount

umount:
	ally-mount -u

opal-loop:
	opal-loop

fresh::	stop
fresh::	rotate
fresh::	server

rotate:
	room-rotate "$$file"

canon:
	ln -sf ../tools/python3_allemande.sh canon/python3-allemande
	$(ALLEMANDE_HOME)/files/canon_links.py $(ALLEMANDE_PATH)
	(cd canon ; rm -f guidance-*.md ; ln -sf ../*/guidance-*.md .)
	ln -sf $(ALLEMANDE_HOME)/canon/usr-local-bin /usr/local/bin
	cd canon ; usr-local-bin python3-allemande confirm uniqo lecho i3-xterm-floating note waywo ally opts opts-long opts-help path-uniq day find-quick need-bash get-root llm query process que proc text-strip cat-named aligno include status-update i3status-wrapper name-terminal name-terminal-nicely mount-point move-rubbish
	cd alias ; usr-local-bin v

fresh-old:: 
	time=$$(date +%Y%m%d-%H%M%S) ; html=$${file%.bb}.html ; \
	if [ -s "$(file)" ]; then mv -v "$(file)" "$(file).$$time"; fi ; \
	if [ -s "$$html" ]; then mv "$$html" "$$html.$$time"; fi ; \
	touch "$(file)" "$$html"

api_doc: llm/llm.api

%.api: %.py
	func -a -I "$<" > "$@"

.PHONY: all default $(JOBS) %.xt canon api_doc subdirs $(SUBDIRS) deps deb-deps venv
