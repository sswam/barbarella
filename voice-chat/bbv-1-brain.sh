#!/bin/bash -eua

nt brain

. ./env-work.sh

chat.py -w "$CHATPATH" -c "/home/sam/allemande/config/llm_llama/experiment.yaml" --delim $'\n' -u "$user" -b "$bot" -n 200 --ignore-shrink --ignore "$user:"
# not: -r --no-trim
