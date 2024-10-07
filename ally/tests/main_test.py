#!/usr/bin/env python3

import os

# Disable DeprecationWarning https://github.com/jupyter/jupyter_core/issues/398
os.environ["JUPYTER_PLATFORM_DIRS"] = "1"

import io
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import tempfile

import main as subject


def test_get_module_name():
    assert subject.get_module_name() == 'main_test'
    assert subject.get_module_name(ext=True) == 'main_test.py'


def test_get_script_name():
    assert subject.get_script_name() == Path(sys.argv[0]).stem
    assert subject.get_script_name(ext=True) == Path(sys.argv[0]).name


def test_get_logger():
    logger = subject.get_logger()
    assert logger.name == 'main_test'


def test_get_log_level():
    with patch('main.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_handler = MagicMock()
        mock_handler.level = 20  # INFO level
        mock_logger.handlers = [mock_handler]
        mock_get_logger.return_value = mock_logger

        assert subject.get_log_level() == 'INFO'


@patch('os.makedirs')
@patch('logging.FileHandler')
@patch('logging.StreamHandler')
@patch('os.chmod')
def test_setup_logging(mock_chmod, mock_stream_handler, mock_file_handler, mock_makedirs):
    """
    Test the setup_logging function to ensure it configures logging correctly.
    """
    mock_logger = MagicMock()
    with patch('main.get_logger', return_value=mock_logger):
        subject.setup_logging('test_module', 'DEBUG')

    mock_makedirs.assert_called_once_with(os.path.expanduser("~/.logs"), exist_ok=True, mode=0o700)
    mock_file_handler.assert_called_once()
    mock_stream_handler.assert_called_once()
    mock_logger.debug.assert_called_with("Starting test_module")
    mock_chmod.assert_called_once()


def test_CustomHelpFormatter():
    formatter = subject.CustomHelpFormatter('test')
    assert isinstance(formatter, subject.argparse.HelpFormatter)


def test_setup_logging_args():
    parser = subject.argparse.ArgumentParser()
    subject.setup_logging_args('test_module', parser)
    args = parser.parse_args([])
    assert hasattr(args, 'log_level')
    assert args.log_level == 'WARNING'  # Default log level


def test_io():
    input_stream = io.StringIO("test input\n")
    output_stream = io.StringIO()
    get, put = subject.io(input_stream, output_stream)

    put("test output")
    assert output_stream.getvalue() == "test output\n"

    result = get()
    assert result == "test input"


def test_resource():
    with patch.dict('os.environ', {'ALLEMANDE_HOME': '/test/path'}):
        path = subject.resource('subdir/file.txt')
        assert str(path) == '/test/path/subdir/file.txt'


def test_IndentLogger():
    mock_logger = MagicMock()
    indent_logger = subject.IndentLogger(mock_logger)

    indent_logger.debug("Test message")
    mock_logger.debug.assert_called_with("Test message")

    indent_logger.indent(1)
    indent_logger.debug("Indented message")
    mock_logger.debug.assert_called_with("\tIndented message")


@patch('pathlib.Path.is_file', return_value=True)
def test_find_in_path(mock_is_file):
    with patch.dict('os.environ', {'PATH': '/fakebin:/usr/fakebin'}):
        assert subject.find_in_path('test_file') == '/fakebin/test_file'


def test_TextInput():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write("test content")
        temp_file_path = temp_file.name

    try:
        text_input = subject.TextInput(temp_file_path)
        assert text_input.display == temp_file_path
        assert text_input.read() == "test content"
    finally:
        os.unlink(temp_file_path)


def test_is_binary():
    assert subject.is_binary('test.jpg') == True
    assert subject.is_binary('test.txt') == False


def test_load():
    mock_file_content = 'line 1\n# line 2\n\nline 3\n'
    expected_output = ['line 1', 'line 3']

    with patch('builtins.open', mock_open(read_data=mock_file_content)) as mock_file:
        result = subject.load('test_file')

    assert result == expected_output
    mock_file.assert_called_once_with(Path(os.environ["ALLEMANDE_HOME"])/'test_file', 'r', encoding='utf-8')