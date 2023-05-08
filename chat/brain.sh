#!/bin/bash -eua

v llama-chat.py -v -m "$LLM_MODEL" -w "$CHATPATH" -c "$ALLEMANDE_HOME/config/llm_llama/experiment.yaml" \
	--delim $'\n' -u "$user" -b "$bot" -n "$TOKEN_LIMIT" --ignore-shrink --ignore "$user:" --get-roles-from-history "$@"

# not using options: -r --no-trim
