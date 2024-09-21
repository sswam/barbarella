"""
Main module for command-line arguments, logging, and utilities.
"""

import os
import sys
import logging
import logging.config
import traceback
import inspect
from pathlib import Path
from typing import TextIO, Callable
import argparse
from io import IOBase, TextIOWrapper

import argh

from ally import terminal

main = sys.modules[__name__]


def get_module_name(level: int = 1, ext: bool = False):
    """
    Get the name of the calling module.

    Args:
        level (int): Stack level to inspect. Default is 1.
        ext (bool): Include file extension if True. Default is False.

    Returns:
        str: Name of the calling module.
    """
    caller_frame = inspect.stack()[level]
    caller_module = inspect.getmodule(caller_frame[0])
    module_name = os.path.basename(caller_module.__file__)
    if ext:
        return module_name
    return os.path.splitext(module_name)[0]


def get_script_name(ext: bool = False):
    """
    Get the name of the current script.

    Args:
        ext (bool): Include file extension if True. Default is False.

    Returns:
        str: Name of the current script.
    """
    script_name = os.path.basename(sys.argv[0])
    if ext:
        return script_name
    return os.path.splitext(script_name)[0]


def get_logger(level=0, indent=False, **kwargs) -> logging.Logger:
    """
    Get a logger for the calling module.

    Returns:
        logging.Logger: Logger instance for the calling module.
    """
    logger = logging.getLogger(main.get_module_name(level + 2))
    if indent:
        logger = main.IndentLogger(logger, **kwargs)
    return logger


def get_log_level() -> str:
    """
    Get the current log level for the console handler.

    Returns:
        str: The current log level.
    """
    return logging.getLevelName(main.get_logger(1).handlers[0].level)


def setup_logging(module_name: str, log_level: str | None = None):
    """
    Set up logging configuration based on the specified log level.
    Also logs to a file at DEBUG level.

    Args:
        module_name (str): The name of the module for which logging is being set up.
        log_level (str): The desired logging level (DEBUG, INFO, ERROR, or None).
    """
    
    logging_config_file = Path(__file__).parent / "logging.ini"

    if log_level is None:
        return

    if isinstance(log_level, str):
        log_level_int = getattr(logging, log_level.upper())
    else:
        log_level_int = log_level
        log_level = logging.getLevelName(log_level_int)

    log_dir = os.path.expanduser("~/.logs")
    os.makedirs(log_dir, exist_ok=True, mode=0o700)
    log_file = os.path.join(log_dir, f"{module_name}.log")

    logger = main.get_logger(2)
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(log_level_int)

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    if log_level_int == logging.DEBUG:
        console_formatter = logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
        )
    else:
        console_formatter = logging.Formatter("%(message)s")

    file_formatter = logging.Formatter(
        "%(asctime)s  PID:%(process)d  %(levelname)-8s  %(name)s  %(message)s"
    )

    ch.setFormatter(console_formatter)
    fh.setFormatter(file_formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    logger.debug(f"Starting {module_name}")

    if False:
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.critical("This is a critical message")

    # Set file permissions to be owner read/write only
    os.chmod(log_file, 0o600)


class CustomHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    - show repr for default values
    - don't show defaults if the defaults is None
    - show .name not repr for stdin and stdout
    - show class name for other IOBase objects
    """

    def _expand_help(self, action):
        """
        Based on ArgumentDefaultsHelpFormatter
        with refernce to argh.constants.CustomFormatter
        """
        params = dict(vars(action), prog=self._prog)
        for name in list(params):
            if params[name] is argparse.SUPPRESS:
                del params[name]
        for name in list(params):
            if hasattr(params[name], "__name__"):
                params[name] = params[name].__name__
        if params.get("choices") is not None:
            choices_str = ", ".join([str(c) for c in params["choices"]])
            params["choices"] = choices_str

        if "default" in params:
            if params["default"] in [None, False]:
                action.default = argparse.SUPPRESS
            elif isinstance(params["default"], IOBase):
                if hasattr(params["default"], "name"):
                    params["default"] = params["default"].name
                else:
                    params["default"] = f"<{params['default'].__class__.__name__}>"
            else:
                params["default"] = repr(params["default"])

        string = self._get_help_string(action) % params
        return string

    def _format_args(self, action, default_metavar):
        if action.dest in ['input', 'output']:
            return 'FILE'
        return super()._format_args(action, default_metavar)


def setup_logging_args(module_name, parser):
    """
    Set up command-line argument parsing for logging options.

    Args:
        module_name (str): The name of the module for which logging is being set up.
        parser (argparse.ArgumentParser): The argument parser to configure.
    """

    # Get the log_level from {SCRIPT_NAME}_LOG_LEVEL, or WARNING.
    log_level_var_name = f"{module_name.upper()}_LOG_LEVEL"
    default_log_level = os.environ.get(log_level_var_name, "WARNING")

    def try_add_argument(*args, **kwargs):
        try:
            parser.add_argument(*args, **kwargs)
        except argparse.ArgumentError as e:
            args = args[1:]
            if not args[0]:
                raise e
            parser.add_argument(*args, **kwargs)

    try_add_argument(
        "-l",
        "--log-level",
        default=default_log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        metavar='LEVEL',
        help="Set the logging level {DEBUG,INFO,WARNING,ERROR,CRITICAL}",
    )
    try_add_argument(
        "-d",
        "--debug",
        action="store_const",
        const=logging.DEBUG,
        dest="log_level",
        help="Set logging level to DEBUG",
    )
    try_add_argument(
        "-q",
        "--quiet",
        action="store_const",
        const=logging.ERROR,
        dest="log_level",
        help="Set logging level to ERROR",
    )
    try_add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const=logging.INFO,
        dest="log_level",
        help="Set logging level to INFO",
    )


def _open_files(args: argparse.Namespace, parser: argparse.ArgumentParser):
    no_clobber = getattr(args, 'no_clobber', False)
    append = getattr(args, 'append', False)

    def process_stream_arg(arg_name, mode='r', append=False, no_clobber=False):
        arg_value = getattr(args, arg_name, None)
        if not isinstance(arg_value, str):
            return
        if mode == 'w':
            mode = 'a' if append else 'x' if no_clobber else 'w'
        file_obj = open(arg_value, mode)
        setattr(args, arg_name, file_obj)

    process_stream_arg('input', mode='r')
    process_stream_arg('output', mode='w', append=append, no_clobber=no_clobber)


def _fix_io_arguments(parser: argparse.ArgumentParser):
    for arg in ['--input', '--output']:
        if arg in parser._option_string_actions:
            action = parser._option_string_actions[arg]
            if action.default == sys.stdin:
                action.help = 'input file'
            elif action.default == sys.stdout:
                action.help = 'stdout'
            action.type = str


def run(command: Callable) -> None:
    """
    Set up logging, parse arguments, and run the specified command.

    Args:
        command (Callable): The command function to be executed.

    Raises:
        Exception: Any exception that occurs during command execution.
    """
    module_name = main.get_module_name(2)

    parser = argh.ArghParser(formatter_class=lambda prog: main.CustomHelpFormatter(prog, max_help_position=40), allow_abbrev=False)

    argh.set_default_command(parser, command)

    main.setup_logging_args(module_name, parser)

    # fix IO args to be strings, and display nicely in help message
    main._fix_io_arguments(parser)

    # Parse arguments without dispatching
    args = parser.parse_args()

    # Open files
    main._open_files(args, parser)

    # Setup logging based on parsed arguments
    main.setup_logging(module_name, args.log_level)

    # dispatch, and show errors nicely
    try:
        argh.dispatching.run_endpoint_function(command, args)
    except Exception as e:
        logger = main.get_logger(1)
        logger.error(f"Error: %s %s", type(e).__name__, str(e))
        tb = traceback.format_exc()
        logger.debug("Full traceback:\n%s", tb)


def io(input: TextIO = sys.stdin, output: TextIO = sys.stdout) -> tuple[Callable, Callable]:
    """
    Create input and output functions for handling I/O operations.

    Args:
        input (TextIO, optional): Input stream. Defaults to sys.stdin.
        output (TextIO, optional): Output stream. Defaults to sys.stdout.

    Returns:
        tuple[Callable, Callable]: A tuple of get and put functions.
    """
    is_tty = terminal.is_terminal(input) and terminal.is_terminal(output)

    def put(*args, end="\n", **kwargs) -> None:
        """
        Print to the output stream.

        Args:
            *args: Positional arguments to print.
            **kwargs: Keyword arguments for print function.
        """
        if args and args[-1].endswith("\n"):
            end = ""
        print(*args, file=output, end=end, **kwargs)

    def get(prompt: str = ": ", all=False) -> str:
        """
        Get input from the input stream.

        Args:
            prompt (str, optional): Prompt to display. Defaults to ": ".

        Returns:
            str: The input string.
        """
        if all:
            return input.read()
        if is_tty:
            terminal.setup_history()
            return terminal.input(prompt)
        else:
            return input.readline().rstrip("\n")

    return get, put


def resource(path: str) -> Path:
    """
    Construct a Path object relative to the ALLEMANDE_HOME environment variable.

    Args:
        path (str): The relative path.

    Returns:
        Path: The constructed Path object.
    """
    parts = path.replace('/', os.sep).split(os.sep)
    return Path(os.environ["ALLEMANDE_HOME"], *parts)


class IndentLogger:
    def __init__(self, logger, indent_str="\t"):
        self.logger = logger
        self.indent_str = indent_str
        self.indent_level = 0

    def indent(self, level):
        self.indent_level += level

    def _log(self, level, msg, *args, **kwargs):
        indented_msg = self.indent_str * self.indent_level + msg
        getattr(self.logger, level)(indented_msg, *args, **kwargs)

    def __getattr__(self, name):
        if name in ['debug', 'info', 'warning', 'error', 'critical']:
            return lambda msg, *args, **kwargs: self._log(name, msg, *args, **kwargs)
        return getattr(self.logger, name)


def find_in_path(file, resolve=True):
    """
    Find a file in the system PATH,
    and resolve symlinks by default.

    Args:
        file (str): The name of the file to find.

    Returns:
        str: The full path to the file if found.

    Raises:
        FileNotFoundError: If the file is not found in PATH.
    """
    for dir in os.environ['PATH'].split(os.pathsep):
        full_path = Path(dir) / file
        if resolve:
            full_path = full_path.resolve()
        if full_path.is_file():
            return str(full_path)
    raise FileNotFoundError(f"{file} (in $PATH)")


class TextInput(TextIOWrapper):
    """
    A text input manager that can read from files or stdin.
    """
    def __init__(self, file=None, mode='r', encoding='utf-8', errors='strict', newline=None, search=False, basename=False, stdin_name='input'):
        if mode not in ('r', 'rb', 'rt'):
             raise ValueError("Mode must be 'r', 'rb', or 'rt'")
        if file in (None, '-', sys.stdin):
            self.display = stdin_name
            super().__init__(sys.stdin.buffer, encoding=encoding, errors=errors, newline=newline)
        elif isinstance(file, str):
            if search and not os.path.exists(file):
                file = find_in_path(file)
            self.display = os.path.basename(file) if basename else file
            super().__init__(open(file, 'rb'), encoding=encoding, errors=errors, newline=newline)
        else:
            super().__init__(file, encoding=encoding, errors=errors, newline=newline)

    def close(self):
        if self.buffer is not sys.stdin.buffer:
            super().close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()