#!/bin/bash

# opts: a simple option parser for bash
# no dependencies, no magic, no bullshit
# )c( Sam Watkins 2009 - 2024
# public domain / MIT

# # usage from bash
# # e.g. for a -debug switch and -mode=foo option:
#
# #!/bin/bash
# # purpose of script
#
# debug=
# mode=normal
# . opts
# if (( debug )); then echo "debug mode"; fi
# echo "mode=$mode"
# echo opts: "${OPTS[@]}"
# echo args: "$@"

# There are three types of options:
# -foo		switch: set foo to 1
# -foo=bar	scalar: set foo to bar
# -foo,a,b,c	array:  set foo to (a b c)

# Note that `-foo bar` is not allowed, use `-foo=bar`.

# To pass an array safely:
#     tool.sh -foo,"${array[*]@Q}"

usage() {
	# read the script itself to output usage:

	case "$*" in
	-h|-help|--help)
		# if -h was passed, not an error: output usage to stdout
		exit=0
		;;
	*)
		# error: if a message was passed, output it to stderr
		exit=1
		exec >&2
		if [ -n "$*" ]; then
			echo "$*"
			echo
		fi
		;;
	esac

	local script_name=$(basename "$0")
	printf "%s " "$script_name"

	local line in_func=0 blanks=0 skip_blank_lines=0
	while IFS= read -r line; do
		# Skip shebang line
		if [[ $line == \#\!* ]]; then
			skip_blank_lines=1
			continue
		fi

		# Skip unindented function declaration, like:  hello() {
		if [[ "$line" =~ ^[[:alnum:]_]+\(\)[[:space:]]*\{ ]]; then
			continue
		fi

		# Remove indent
		line=${line#[[:space:]]*}

		is_blank=0
		if [ "$line" = "" ]; then
			is_blank=1
		fi

		# Remove 'local ' from start of line
		line=${line/#local /'  '}

		# Remove '# ' from start of line
		line="${line#\# }"

		# Replace literal '$0' in lines with the value of $script_name
		line="${line//\$0 /$script_name }"

		# Stop before the ". opts" line
		if [[ "$line" =~ ^[:space:]*\.\ opts ]]; then
			break
		fi

		# Skip other ". " lines
		if [[ "$line" =~ ^[:space:]*\.\  ]]; then
			continue
		fi

		# avoid trailing blank lines
		if [ "$is_blank" = 1 ]; then
			blanks=$((blanks+1))
			continue
		fi

		# check if we have some blank lines, and squeeze them
		if [ $blanks -gt 0 ] && [ $skip_blank_lines -eq 0 ]; then
			echo
		fi
		blanks=0
		skip_blank_lines=0

		# echo the cleaned-up line, for usage
		echo "$line"
	done < "$0"

	exit $exit
}

OPTS_UNKNOWN=()
OPTS=()
OPTS_N=0

opts_set_scalar() {
	local type=$1 OPT=$2 VAL=$3

	# check that $OPT is declared
	if [ "$type" == "" ]; then
		usage "error: not declared: $OPT"
	fi

	# check that $OPT is declared as a string or an int
	if [ "$type" != "string" ] && [ "$type" != "int" ]; then
		usage "error: not a scalar: $OPT"
	fi

	# check int
	if [ "$type" = "int" ] && ! [[ $VAL =~ ^[0-9]+$ ]]; then
		usage "error: not an int: $OPT=$VAL"
	fi

	eval $OPT=\$VAL
}

opts_set_array() {
	local type=$1 OPT=$2 VAL=$3 SEP=$4

	# check that $OPT is declared as an array
	if [ "$type" != "array" ]; then
		usage "error: not an array: $OPT"
	fi

	# if OPTVAL is foo,a,b,c
	# then set OPT as an array to (a b c)

	local IFS=$SEP
	eval $OPT=\($VAL\)
}

while [ $# -gt 0 ]; do
	case "$1" in
	"")
		break
		;;
	-)
		break
		;;
	--)
		shift
		;;
	-h|-help|--help)
		usage -h
		;;
	[!-]*)
		break
		;;
	esac

	OPTS[$OPTS_N]="$1"
	OPTVAL="${1#-}"
	OPTVAL="${OPTVAL#-}"

	OPT=${OPTVAL%%[=, ]*}
	OPT="${OPT//-/_}"

	OP=${OPTVAL:${#OPT}:1}
	VAL=${OPTVAL:$[${#OPT}+1]}

	# if $OPT doesn't start with a letter, add opt_ prefix
	if ! [[ $OPT =~ ^[a-zA-Z] ]]; then
		OPT="opt_$OPT"
	fi

	OPTS_DECLARATION=$(declare -p "$OPT" 2>/dev/null || true)

	case "$OPTS_DECLARATION" in
	declare\ -a*)
		type=array
		;;
	declare\ -i*)
		type=int
		;;
	"")
		type=""
		;;
	*)
		type=string
		;;
	esac

	if [ -z "$type" ]; then
		OPTS_UNKNOWN+=("$OPT")
	fi

	case "$OP" in
	=)
		opts_set_scalar "$type" "$OPT" "$VAL"
		;;
	,)
		opts_set_array "$type" "$OPT" "$VAL" ","
		;;
	" ")
		opts_set_array "$type" "$OPT" "$VAL" " "
		;;
	"")
		opts_set_scalar "$type" "$OPT" 1
		;;
	*)
		usage "error: unknown operator: $OP"
		;;
	esac
	shift
	OPTS_N=$[$OPTS_N + 1]
done

if [ ${#OPTS_UNKNOWN[@]} -gt 0 ]; then
	usage "error: unknown options: ${OPTS_UNKNOWN[*]}"
fi