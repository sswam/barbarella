#!/usr/bin/env python3

"""
indent_tool.py - detect and apply indentation styles

This script can detect the indentation type and level of input text,
and can also reindent the input according to specified parameters.

Usage as a module:
    from indent_tool import process_indentation
"""

import os
import sys
import re
from typing import TextIO, Tuple, Optional
from collections import Counter

from argh import arg

from ally import main

__version__ = "1.0.0"

logger = main.get_logger()

DEFAULT_INDENT = os.environ.get("INDENT", "t")

def detect_indent(text: str) -> Tuple[str, int]:
    """Detect the indentation type and minimum level of the input text."""
    # Remove empty lines and get non-empty lines
    lines = text.splitlines()
    lines = [line for line in lines if line.strip()]

    # Find the common indentation among all lines
    common_indent = None
    for line in lines:
        indent_size = len(line) - len(line.lstrip())
        indent = line[:indent_size]
        if common_indent is None or indent_size < len(common_indent):
            common_indent = indent

    if common_indent is None:
        common_indent = ""

    # Check for invalid indentation characters
    if re.search(r"[^\s\t]", common_indent):
        raise ValueError("Whitespace other than spaces and tabs in indentation")

    if "\t" in common_indent and " " in common_indent:
        raise ValueError("Mixed tabs and spaces in common indentation")

    common_indent_length = len(common_indent)

    # Remove common indentation from all lines
    stripped_lines = [line[common_indent_length:] for line in lines]

    # Count spaces and tabs at the beginning of each line
    spaces = re.compile(r"^ +")
    tabs = re.compile(r"^\t+")

    space_counts = [
        len(spaces.match(line).group()) if spaces.match(line) else 0
        for line in stripped_lines
    ]
    tab_counts = [
        len(tabs.match(line).group()) if tabs.match(line) else 0
        for line in stripped_lines
    ]

    logger.debug(space_counts)
    logger.debug(tab_counts)
    total_spaces = sum(space_counts)
    total_tabs = sum(tab_counts)

    # Helper function to find the greatest common divisor
    def find_common_factor(a, b):
        while b:
            a, b = b, a % b
        return a

    # Determine indentation type and size based on counts and common indentation
    if not common_indent and total_spaces == total_tabs == 0:
        indent_type = ""
        indent_size = 0
    elif "\t" in common_indent or total_tabs * 2 > total_spaces:
        indent_type = "t"
        indent_size = 1
    elif not total_spaces:
        indent_type = "s"
        if common_indent_length % 4 == 0:
            indent_size = 4
        elif common_indent_length % 2 == 0:
            indent_size = 2
        else:
            indent_size = 1
    else:
        indent_type = "s"
        # Find the most common indent size
        indent_size_freq = Counter(
            count for count in space_counts if count > 0 and count <= 8
        ).most_common(2)
        indent_size = indent_size_freq[0][0]
        indent_size_2 = indent_size_freq[1][0] if len(indent_size_freq) > 1 else None
        indent_size = find_common_factor(
            find_common_factor(indent_size, indent_size_2), common_indent_length
        )
        if indent_size == 1:
            logger.warning("Indent detected is one space, sounds like a bad idea")

    # Calculate the minimum indentation level
    min_level = common_indent_length // indent_size if indent_size else 0

    assert (
        indent_type != "t" or indent_size == 1
    ), f"Indent type is tab but indent size is nott 1: {indent_size}"

    logger.debug(f">> {indent_size=}, {indent_type=}, {min_level=}")

    return indent_size, indent_type, min_level


def apply_indent(text: str, indent_size: int, indent_type: str, min_level: int) -> str:
    """Apply the specified indentation to the input text."""

    # Detect the original indentation of the input text
    orig_indent_size, orig_indent_type, orig_min_level = detect_indent(text)

    lines = text.splitlines()

    # Create indent strings for original and new indentation
    orig_indent_str = "\t" if orig_indent_type == "t" else " " * orig_indent_size
    orig_min_indent = orig_indent_str * orig_min_level

    indent_str = "\t" if indent_type == "t" else " " * indent_size
    min_indent = indent_str * min_level

    def reindent_line(line: str) -> str:
        # Remove trailing whitespace and original minimum indentation
        line = line.rstrip()
        line_without_min_indent = line[len(orig_min_indent) :]

        # Extract indentation and text content of the line
        line_indent_str, line_text = re.match(r"^(\s*)(.*)$", line_without_min_indent).groups()
        line_indent = len(line_indent_str) // orig_indent_size if orig_indent_size else 0

        # Apply new indentation
        new_indent = min_indent + indent_str * line_indent
        new_line = new_indent + line_text
        return new_line

    # Apply reindentation to all lines and join them
    return "\n".join(reindent_line(line) for line in lines) + "\n"


def format_indent_code(indent_size: int, indent_type: str, min_level: int) -> str:
    """Format the indent code for display."""
    # Convert indentation parameters to a string representation
    min_level = min_level or ""
    if indent_type == "t":
        if indent_size != 1:
            raise ValueError(f"Invalid indent size for tab: {indent_size}")
        return f"t{min_level}"
    return f"{indent_size}s{min_level}"


def parse_indent_code(indent_code: str) -> Tuple[str, int, int]:
    """Parse the indent code into its components."""
    # Extract indent size, type, and minimum level from the indent code string
    match = re.match(r"([1-8])?(t|s)(\d*)$", indent_code)
    if not match:
        raise ValueError(f"Invalid indent code: {indent_code}")
    indent_size, indent_type, min_level = match.groups()
    if not indent_size:
        indent_size = 4 if indent_type == "s" else 1
    return int(indent_size), indent_type, int(min_level or 0)


@arg("--detect", "-D", help="detect indent type and minimum level")
@arg("--apply", help="apply specified indent type and minimum level (e.g., '1t', '4s2')")
def process_indentation(
    input: TextIO = sys.stdin,
    output: TextIO = sys.stdout,
    detect: bool = False,
    apply: Optional[str] = DEFAULT_INDENT,
) -> None:
    """
    Detect or apply indentation to the input text.

    Environment:
        INDENT: default indent to use when not specified

    Examples:
        indenter.py --detect < input.txt
        indenter.py --apply 4s2 < input.py > output.py
        indenter.py --apply t < input.c > output.c
        indenter.py < input.sh > output.sh  # uses default indent
    """
    # Set up input and output streams
    get, put = main.io(input, output)

    input_text = get(all=True)

    if detect:
        # Detect and output the indentation of the input text
        put(format_indent_code(*detect_indent(input_text)))
    else:
        # Apply the specified or default indentation to the input text
        indent_code = apply or DEFAULT_INDENT
        output_text = apply_indent(input_text, *parse_indent_code(indent_code))
        put(output_text)


if __name__ == "__main__":
    main.run(process_indentation)