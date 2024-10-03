#!/usr/bin/env python3

"""
This module splits textual input on sensible boundaries so that the token count
is under a given limit, and above a given lower limit.
"""

import sys
import logging
from typing import TextIO, Callable, Generator
from math import ceil

from argh import arg
import llm

from ally import main
from ally.lazy import lazy

__version__ = "0.1.0"

logger = main.get_logger()


def count_tokens(text: str, model: str) -> int:
    """Count tokens for the given text using the specified model."""
    return llm.count(text, model)


def count_chars(text: str, _: str) -> int:
    """Count characters in the given text."""
    return len(text)


def count_words(text: str, _: str) -> int:
    """Count words in the given text."""
    return len(text.split())


def count_sentences(text: str, _: str) -> int:
    """Count sentences in the given text."""
    return len(text.split('.'))


def count_lines(text: str, _: str) -> int:
    """Count lines in the given text."""
    return len(text.splitlines())


def get_count_function(count_type: str) -> Callable[[str, str], int]:
    """Return the appropriate count function based on the count type."""
    count_functions = {
        'token': count_tokens,
        'char': count_chars,
        'word': count_words,
        'sentence': count_sentences,
        'line': count_lines,
    }
    return count_functions.get(count_type, count_tokens)


def split_text(text: str, max_count: int, min_count: int, count_func: Callable[[str, str], int], model: str) -> Generator[str, None, None]:
    """Split the text into chunks based on the given criteria."""
    lines = text.splitlines()
    current_chunk = []
    current_count = 0

    for line in lines:
        line_count = count_func(line, model)
        if current_count + line_count > max_count and current_chunk:
            yield '\n'.join(current_chunk)
            current_chunk = []
            current_count = 0

        current_chunk.append(line)
        current_count += line_count

        if line.startswith('# ') and current_count >= min_count:
            yield '\n'.join(current_chunk)
            current_chunk = []
            current_count = 0
        elif line.startswith('## ') and current_count >= min_count:
            yield '\n'.join(current_chunk)
            current_chunk = []
            current_count = 0

    if current_chunk:
        yield '\n'.join(current_chunk)


def parse_percentage(value: str) -> float:
    """Parse a percentage string or float."""
    if isinstance(value, float):
        return value
    if value.endswith('%'):
        return float(value[:-1]) / 100
    return float(value)


@arg('--model', help='Specify the model for token counting')
@arg('--count-type', choices=['token', 'char', 'word', 'sentence', 'line'], default='token', help='Specify the counting method')
@arg('--max-count', type=int, help='Maximum count per chunk')
@arg('--min-count', type=int, help='Minimum count per chunk')
@arg('--num-chunks', type=int, help='Desired number of chunks')
@arg('--deviation', type=str, help='Maximum deviation from average chunk size (e.g., 0.2 or 20%)')
def chunk(
    *filenames: str,
    istream: TextIO = sys.stdin,
    ostream: TextIO = sys.stdout,
    model: str = 'gpt-3.5-turbo',
    count_type: str = 'token',
    max_count: int | None = None,
    min_count: int | None = None,
    num_chunks: int | None = None,
    deviation: str | None = None,
) -> None:
    """
    Split textual input on sensible boundaries so that the count is under a given limit,
    and above a given lower limit.
    """
    get, put = main.io(istream, ostream)

    text = get()
    count_func = get_count_function(count_type)
    total_count = count_func(text, model)

    if num_chunks:
        avg_count = total_count / num_chunks
        if deviation:
            dev = parse_percentage(deviation)
            max_count = int(avg_count * (1 + dev))
            min_count = int(avg_count * (1 - dev))
        else:
            max_count = int(avg_count * 1.2)
            min_count = int(avg_count * 0.8)
    else:
        if not max_count:
            max_count = total_count
        if not min_count:
            min_count = max_count // 2

    logger.info(f"Splitting text with {count_type} count. Max: {max_count}, Min: {min_count}")

    chunks = list(split_text(text, max_count, min_count, count_func, model))

    for i, chunk in enumerate(chunks, 1):
        chunk_count = count_func(chunk, model)
        put(f"--- Chunk {i} ({chunk_count} {count_type}s) ---")
        put(chunk)
        put()

    logger.info(f"Split into {len(chunks)} chunks")

    if filenames:
        put()
        put("I see you also offered me some files, but I'm not processing them.")
        put("This script works with stdin/stdout by default.")


if __name__ == "__main__":
    main.run(chunk)