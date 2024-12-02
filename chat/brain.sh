#!/bin/bash
#
# Run the LLM chatbot with the specified settings

. unset-option-vars
OPTS_ALLOW_UNKNOWN=1 eval "$(ally)"

v ally-chat -v -m "$LLM_MODEL" -w "$WATCH_LOG" -c "$ALLEMANDE_HOME/config/llm_llama/experiment.yaml" "$@"

# not using options: -r --no-trim --get-roles-from-history
# -u "$user" -b "$bot" 
# --ignore "$user:"
