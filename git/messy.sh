#!/bin/bash
# [options] [files]
# Commit to Git, with a message generated by an LLM.

# Ensure Bash version 4 or higher for associative arrays
if ((BASH_VERSINFO[0] < 4)); then
    echo "Error: This script requires Bash 4.0 or higher." >&2
    exit 1
fi

. confirm

diff_context=5  # lines of context for diffs
model="d"       # default model
# initial_bug_check=1  # check for bugs before generating commit message

timestamp=$(date +%Y%m%d%H%M%S)
commit_message="commit-message.$timestamp.$$.txt"
review="review.$timestamp.$$.txt"

# Associative arrays mapping model codes to names and options
declare -A model_names=(
    ["4"]="GPT-4"
    ["4m"]="GPT-4o-mini"
    ["op"]="OpenAI o1"
    ["om"]="OpenAI o1-mini"
    ["c"]="Claude"
    ["i"]="Claude Instant"
    ["g"]="Gemini 1.5 Pro"
    ["f"]="Gemini 1.5 Flash"
)

declare -A option_model_codes=(
    ["3"]="4m"
    ["4"]="4"
    ["c"]="c"
    ["i"]="i"
    ["M"]="om"
    ["o"]="op"
    ["g"]="gp"
    ["f"]="gf"
)

usage() {
    echo "Usage: `basename "$0"` [-4|-3|-c|-i|-o|-M|-g|-f] [-n] [-C lines] [-B] [-m msg] [-F file] [-e] [-h]"
    echo "  -n: start at menu, do not generate"
    for opt in "${!option_model_codes[@]}"; do
        model_code="${option_model_codes[$opt]}"
        model_name="${model_names[$model_code]}"
        echo "  -$opt: generate with $model_name"
    done
    echo "  -n: start at menu, do not generate"
    echo "  -C: set the number of lines of context for diffs"
    echo "  -B: skip initial bug check"
    echo "  -m: use the given message instead of generating one"
    echo "  -F: use the given message in a file"
    echo "  -e: normal git commit using the editor"
    echo "  -h: show this help message"
    echo "  -x: clean up commit-message.*.txt files"
}

if type move-rubbish >/dev/null 2>&1; then
    MR=move-rubbish
else
    MR="rm -f"
fi

# Run git with retries to handle index.lock errors
git() {
    stderr=$(mktemp)
    for i in {1..5}; do
        command git "$@" 2> "$stderr"
        if [ $? -eq 0 ]; then
            break
        fi
        # look for Unable to create .* index.lock
        if ! grep -q 'Unable to create .* index.lock' "$stderr"; then
            break
        fi
        sleep .$RANDOM
    done
    rm -f "$stderr"
}

cleanup() {
    # Remove empty commit messages that are not open
    find . -type f -name 'commit-message.*.txt' -size 0 2>/dev/null | while read -r file; do
        if ! lsof "$file" >/dev/null 2>&1; then
            rm -v "$file"
        fi
    done
}

get_lock() {
    while ! mkdir "$git_root/.git/messy.lock" 2>/dev/null; do
        echo >&2 "Waiting for messy.lock to be released..."
        sleep .$RANDOM
    done
}

release_lock() {
    rmdir "$git_root/.git/messy.lock" 2>/dev/null || true
}

cleanup-and-exit() {
    release_lock
    $MR "$review" "$commit_message" 2>/dev/null
    exit "$1"
}

message-and-exit() {
    release_lock
    echo >&2
    echo >&2 "Messages:"
    echo >&2 "  $commit_message"
    echo >&2 "  $review"
    exit "$1"
}

git-commit() {
    get_lock
    git add -A -- "${files[@]:-.}"
    git commit "$@" "${files[@]:-.}"
    release_lock
}

trap 'cleanup-and-exit 0' EXIT
trap 'message-and-exit 1' INT

run_initial_gens=1

while getopts "nC:B43cioMm:F:exh" opt; do
    case "$opt" in
    n)
        run_initial_gens=0
        ;;
    C)
        diff_context="$OPTARG"
        ;;
#     B)
#         initial_bug_check=0
#         ;;
    m)
        echo "$OPTARG" > "$commit_message"
        model=""
        run_initial_gens=0
        ;;
    F)
        cp "$OPTARG" "$commit_message"
        model=""
        run_initial_gens=0
        ;;
    e)
        git-commit
        exit 0
        ;;
    x)
        cleanup
        exit 0
        ;;
    h)
        usage
        exit 0
        ;;
    *)
        if [[ -n "${option_model_codes["$opt"]}" ]]; then
            model="${option_model_codes["$opt"]}"
        else
            usage
            exit 1
        fi
        ;;
    esac
done
shift $((OPTIND-1))

# handle the list of files

files=( "$@" )

original_dir=$PWD

# Try to find the repo containing the first file

resolve_symlinks=0

file0=${files[0]}

if [ -n "$file0" -a ! -e "$file0" ]; then
    file0=$(which-file "$file0")
fi

# Find the repo containing the first file
if [ -n "$file0" ]; then
    git_root=$(cd "$(dirname "$file0")"; git rev-parse --show-toplevel)
fi

# If that fails, try to resolve the first file as a symlink to find the repo
if [ -n "$file0" -a -z "$git_root" ]; then
    resolve_symlinks=1
    file0=$(realpath "$file0")
    git_root=$(cd "$(dirname "$file0")"; git rev-parse --show-toplevel)
fi

# If that fails, use the current directory, e.g. if no files were given
if [ -z "$git_root" ]; then
    git_root=$(git rev-parse --show-toplevel)
fi

if [ -z "$git_root" ]; then
    exit 1
fi

# if no files were given, use staged

get_lock

if [ "${#files[@]}" -eq 0 ]; then
    cd "$git_root"
    readarray -t files < <(git-mod staged)
else
    git add -A -- "${files[@]}"
fi

# if still no files, use all
if [ "${#files[@]}" -eq 0 ]; then
    cd "$original_dir"
    git add -A .
    cd "$git_root"
    readarray -t files < <(git-mod staged)
fi

release_lock

if [ "${#files[@]}" -eq 0 ]; then
    echo >&2 "No files to commit."
    exit 1
fi

# Find any missing files
for i in "${!files[@]}"; do
    if [ ! -L "${files[$i]}" ] && [ ! -e "${files[$i]}" ]; then
        if [ -n "$(git status --porcelain -- "${files[$i]}")" ]; then
            continue
        fi
        found=$(which-file "${files[$i]}")
        if [ -z "$found" ]; then
            echo >&2 "File not found: ${files[$i]}"
            exit 1
        fi
        files[$i]=$found
        if [ "$resolve_symlinks" -eq 1 ]; then
            files[$i]=$(realpath "${files[$i]}")
        fi
    fi
done

# Paths relative to git_root
for i in "${!files[@]}"; do
    files[$i]=$(realpath --no-symlinks --relative-to="$git_root" "${files[$i]}")
    # if outside the repo, remove it from the list
    if [ "${files[$i]:0:3}" = "../" ]; then
        echo >&2 "Skipping file outside repo: ${files[$i]}"
        unset files[$i]
    fi
done

files=("${files[@]}")

cd "$git_root"

# Make sure all files are added
for file in "${files[@]}"; do
    git add -- "$file"
done


# Add former names of renamed files
# i.e. for every file in "${files[@}",
# I need to add its former name to that files array.
deleted_files=($(git ls-files --deleted))
if [ ${#deleted_files[@]} -gt 0 ]; then
    git rm -- "${deleted_files[@]}"
fi
while IFS=$'\t' read -r status from to; do
    # check if from is in files array, the long way
    for i in "${!files[@]}"; do
        if [ "${files[$i]}" = "$to" ]; then
            files+=("$from")
            break
        fi
    done
done < <(git diff --staged --name-status | grep '^R')
if [ ${#deleted_files[@]} -gt 0 ]; then
    git restore --staged -- "${deleted_files[@]}"
fi


# Inform the user of the files to be committed
echo "Files to commit:"
for file in "${files[@]}"; do
    echo "  $file"
done
echo

model-name() {
    local name="${model_names["$1"]}"
    if [ -z "$name" ]; then
        case "$1" in
            d) name="$ALLEMANDE_LLM_DEFAULT" ;;
            s) name="$ALLEMANDE_LLM_DEFAULT_SMALL" ;;
            *) name="[unknown model: $1]" ;;
        esac
    fi
    echo "$name"
}

run-git-diff() {
    get_lock
    local opts=("$@")
    local difftext
    v git add -A -- "${files[@]}"
    v git diff --staged -U$diff_context --find-renames "${opts[@]}" -- "${files[@]}" |
    grep -v -e '^\\ No newline at end of file$' -e '^index '
#
#     if [ "${#files[@]}" -eq 0 ]; then
#         git diff --staged -U$diff_context --find-renames -- "${opts[@]}"
#     else
#         git add -A -- "${files[@]}"
#         for file in "${files[@]}"; do
#             difftext=$(git diff --staged -U$diff_context --find-renames "${opts[@]}" -- "$file")
#             if [ -n "$difftext" ]; then
#                 printf "%s\n" "$difftext"
#             elif [ -e "$file" ] && [ -n "$(git ls-files --exclude-standard --others --directory --no-empty-directory --error-unmatch "$file" 2>/dev/null)" ]; then
#                 cat-named "$file"
#             fi
#         done
#     fi
    release_lock
}

run-git-diff-two-stage() {
# TODO maybe this was a good idea, but we don't want to send whole files twice
#   when adding new files.
#     echo "## ACTUAL CHANGES; ONLY DESCRIBE THESE"
#     run-git-diff | grep '^[-+]'
#     echo
#     echo "## CONTEXT; DO NOT DESCRIBE THIS"
    run-git-diff
    echo
}

generate-commit-message() {
    model="$1"
    echo "Generating commit message using $(model-name "$model") ..."
    if [ -e "$commit_message" ]; then
        echo >&2 "Commit message already exists: $commit_message, moving it to rubbish."
        $MR "$commit_message"
    fi

    run-git-diff | llm process -m "$model" "## First Task

Please describe this diff, for a high-level Conventional Commits message.
You know how to read a diff. Lines that are not preceded with + or - is just CONTEXT.
We won't commit on the context as if it was newly added, right?! :)

*** Only describe the ACTUAL CHANGES, not the CONTEXT. ***
Return only the git commit message, no prelude or conclusion.

Format of the header line:

feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert(short-module-name): a summary line, 50-70 chars

Anything that changes functionality in any way is a feature, not a refactor.
Please mark fixes as fix, not feat. I make a lot of fixes.

Files in the 'snip' directory, are obsolete rubbish that's been removed from something else.
Files in the 'gens' directory, are interesting AI generated content, but it is not important.

After the header line you may list more details, starting each with a dash, but
ONLY if it's really needed. NEVER add redundant details that are already
covered in the header line, and don't explain what you did:

- Describe each change very concisely, if not already covered in the header;
  as few list items as possible.
- Continuing lines are indented with two spaces, as shown.

Write very concisely in a down-to-earth tone.
*** DO NOT use market-speak words like 'enhance', 'streamline'. ***
We don't want too much detail or flowery language, short and sweet is best.

## Second Task

Please carefully review this patch with a fine-tooth comb. Important: DON'T
WRITE ANYTHING if it is bug-free and you see no issues, or list bugs still
present in the patched code. Do NOT list bugs in the original code that are
fixed by the patch. Also list other issues or suggestions if they seem
worthwhile. Especially, check for sensitive information such as private keys or
email addresses that should not be committed to git. Adding the author's email
deliberately is okay. Also note any grossly bad code or gross inefficiencies.
If you don't find anything wrong, don't write anything for this task so as not
    to waste both of our time. Thanks!

Expected format:

1. bug or issue
2. another bug or issue

Or if nothing is wrong, please DON'T WRITE ANYTHING for the second task, just
the commit message for the first task. Thanks for being awesome!
" | grep -v '^```' | perl -e '
    @lines = <STDIN>;
    if (@lines && $lines[0] =~ /:$/) {
        warn "removing header: $lines[0]\n";
        shift @lines;
        if (@lines && $lines[0] =~ /^$/) {
            shift @lines;
        }
    }
    print join("", @lines);
' | fmt -s -w 78 -g 78 | fmt-commit > "$commit_message"
    echo
}

# check-for-bugs() {
#     model="$1"
#     echo "Checking for bugs using $(model-name "$model") ..."
#     if [ -e "$review" ]; then
#         echo >&2 "Code review already exists: $review, moving it to rubbish."
#         $MR "$review"
#     fi
#     run-git-diff --color
#     run-git-diff | proc -m="$model" "Please carefully review this patch with a fine-tooth comb
# Answer LGTM if it is bug-free and you see no issues, or list bugs still present
# in the patched code. Do NOT list bugs in the original code that are fixed by
# the patch. Also list other issues or suggestions if they seem worthwhile.
# Especially, check for sensitive information such as private keys or email
# addresses that should not be committed to git. Adding the author's email
# deliberately is okay. Also note any grossly bad code or gross inefficiencies.
# If you don't find anything wrong, just say 'LGTM' only, so as not to waste both of our time. Thanks!
# 
# Expected format:
# 
# 1. bug or issue
# 2. another bug or issue
# 
# or if nothing is wrong, please just wrte 'LGTM'.
# " | fmt -s -w 78 -g 78 | tee "$review"
#     echo
# }

if (( run_initial_gens )); then
#     if [ "$initial_bug_check" -eq 1 ]; then
#         check-for-bugs "$model"
#     fi
    if [ ! -e "$review" ] || [ "$(cat "$review")" = "LGTM" ]; then
        generate-commit-message "$model"
    fi
fi

run-git-vimdiff() {
    if [ "${#files[@]}" -eq 0 ]; then
        git-vimdiff-staged
    else
        git-vimdiff "${files[@]}"
    fi
}

edit-files() {
    $EDITOR ${EDITOR_SPLIT_OPTS:--O} "${files[@]}"
}


while true; do
    if [ -e "$commit_message" ]; then
        cat "$commit_message"
        echo
        prompt="Commit with this message?"
    else
        prompt="Action?"
    fi
    read -p "$prompt [y/n/q/e/3/4/c/i/o/M/g/f/d/v/b/E/x/?] " -n 1 -r choice
    echo
    case "$choice" in
        y)
            break
            ;;
        n|q)
            cleanup-and-exit 1
            ;;
        e)
            ${EDITOR:-vi} "$commit_message"
            ;;
        d)
            run-git-diff --color | less -F -X -e -i -M -R -W -z-4
            ;;
        v)
            run-git-vimdiff
            ;;
#         b)
#             check-for-bugs "${model:-d}"
#             ;;
        E)
            edit-files
            ;;
        x)
            cleanup
            ;;
        $'\x0c')
            clear
            ;;
        \?|h|"")
            echo "Available actions:"
            echo "  y: commit with this message"
            echo "  n/q: abort"
            echo "  e: edit the message"
            for ch in "${!option_model_codes[@]}"; do
                model_code="${option_model_codes["$ch"]}"
                model_name="${model_names["$model_code"]}"
                echo "  $ch: generate with $model_name"
            done
            echo "  d: diff the staged changes"
            echo "  v: vimdiff the staged changes"
#            echo "  b: check for bugs"
            echo "  E: edit the files"
            echo "  ?: show this help message"
            echo "  x: clean up commit-message.*.txt files"
            echo
            ;;
        *)
            if [[ -n "${option_model_codes["$choice"]}" ]]; then
                generate-commit-message "$choice"
            else
                echo >&2 "Invalid choice"
            fi
            ;;
    esac
    echo
done

git-commit -F "$commit_message"
