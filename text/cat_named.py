#!/usr/bin/env python3

"""
This module concatenates and displays file contents with customizable headers.

It can be used to read and display the contents of multiple files or URLs,
with options to add headers, numbering, and customize the output format.
"""

import os
import sys
import logging
from pathlib import Path
import subprocess
from urllib.parse import urlparse
import re
import argparse
from typing import List, Callable

from ally import main

__version__ = "1.0.2"

logger = main.get_logger()


def get_web_content(url: str) -> str:
    """Fetch content from a URL using web_text tool."""
    try:
        result = subprocess.run(
            ["web_text", url], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise FileNotFoundError(f"Failed to fetch content from {url}: {e}")


def number_the_lines(text: str) -> str:
    """Number the lines in the text, just number, tab, and line."""
    lines = text.splitlines()
    return "\n".join(f"{i+1}\t{line}" for i, line in enumerate(lines))


def cat_named(
    put: Callable[str, None],
    sources: List[str],
    header_prefix: str = "#File: ",
    header_suffix: str = "\n\n",
    footer: str = "\n\n",
    number: int | None = None,
    number_suffix: str = ". ",
    path: bool = False,
    basename: bool = False,
    stdin_name: str | None = "input",
    missing_ok: bool = False,
    number_lines: bool = False,
) -> str:
    """
    Concatenate and return file or URL contents with customizable headers.
    """

    def get_header(source: str) -> str:
        nonlocal number
        if number is not None:
            header = f"{header_prefix}{number}{number_suffix}{source}"
            number += 1
        else:
            header = f"{header_suffix}{source}"
        return header

    for source in sources:
        is_url = source.startswith(("http://", "https://", "ftp://", "ftps://"))

        if is_url and basename:
            display_name = os.path.basename(urlparse(source).path)
        elif is_url:
            display_name = source
        elif basename:
            display_name = Path(source).name
        else:
            display_name = source

        try:
            if is_url:
                content = get_web_content(source)
            else:
                with main.TextInput(
                    source, search=path, basename=basename, stdin_name=stdin_name
                ) as istream:
                    content = istream.read()
                    display_name = istream.display

            header = get_header(display_name)

            put(f"{header}{header_suffix}")
            if number_lines:
                content = number_the_lines(content)
            put(content)
            put(footer)
        except (FileNotFoundError, IsADirectoryError):
            if missing_ok:
                header = get_header(display_name)
                put(f"{header} (content missing){header_suffix}")
                put(footer)
            else:
                raise


def setup_args(parser: argparse.ArgumentParser) -> None:
    """Set up the command-line arguments."""
    parser.description = "Concatenate and display file contents with customizable headers."
    parser.add_argument("sources", nargs="*", help="Files or URLs to concatenate and display")
    parser.add_argument("-n", "--number", type=int, help="Number the files starting from this value")
    parser.add_argument("-p", "--path", action="store_true", help="Search for files in PATH")
    parser.add_argument("-b", "--basename", action="store_true", help="Use only the basename of the file in the header")
    parser.add_argument("-f", "--missing-ok", action="store_true", help="Skip missing files without error")
    parser.add_argument("-N", "--number-lines", action="store_true", help="Number the lines in the output")
    parser.add_argument("-P", "--header-prefix", help="Prefix for the header line")
    parser.add_argument("-S", "--header-suffix", help="Suffix for the header line")
    parser.add_argument("-F", "--footer", help="String to append after each file's content")
    parser.add_argument("--stdin-name", help="Use this name for stdin")
    parser.add_argument("--number-suffix", help="String to append after the number in the header")


if __name__ == "__main__":
    main.go(setup_args, cat_named)
