# AUTOGENERATED! DO NOT EDIT! File to edit: ../blog/posts/multilabel2/multilabel2.ipynb.

# %% auto 0
__all__ = ['p', 'redirect_stderr_to_dev_null', 'powerset', 'seq_diff', 'join_a_foo_and_a_bar', 'confirm_delete', 'setup_logging',
           'add_logging_options', 'redirect', 'git_root', 'export']

# %% ../blog/posts/multilabel2/multilabel2.ipynb 5
import sys
import os
from fastcore.foundation import L
from pathlib import Path
from fastcore.xtras import Path

# %% ../blog/posts/multilabel2/multilabel2.ipynb 8
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'

# %% ../blog/posts/multilabel2/multilabel2.ipynb 10
from itertools import chain, combinations

def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

# %% ../blog/posts/multilabel2/multilabel2.ipynb 11
def seq_diff(s1, s2):
    return L(filter(lambda x: x not in s2, s1))

# %% ../blog/posts/multilabel2/multilabel2.ipynb 14
import inflect

p = inflect.engine()

# %% ../blog/posts/multilabel2/multilabel2.ipynb 15
def join_a_foo_and_a_bar(comb):
    return " and ".join(p.a(x) for x in comb)

# %% ../blog/posts/multilabel2/multilabel2.ipynb 18
import ipywidgets as widgets
from send2trash import send2trash

def confirm_delete(del_path):
    button = widgets.Button(description=f"Move data to trash: {del_path}?", layout=widgets.Layout(width='20em'))
    # button.on_click(lambda b: shutil.rmtree(del_path, ignore_errors=True))
    button.on_click(lambda b: send2trash(del_path))
    display(button)

# %% ../blog/posts/multilabel2/multilabel2.ipynb 22
import logging

def setup_logging(args):
    """ Set up logging. """

    # get basename of program in upper case
    prog_name_uc = os.path.basename(sys.argv[0]).upper()

    log_file = args.log or os.environ.get(f'{prog_name_uc}_LOG')
    fmt = "%(message)s"
    if args.log_level == logging.DEBUG:
        fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"

    # if a log_file was specified, use it
    log_file = log_file or os.environ.get('CHATGPT_LOG_FILE')
    logging.basicConfig(level=args.log_level, format=fmt, filename=log_file)

def add_logging_options(parser):
    """ Add logging options to an argument parser. """
    logging_group = parser.add_argument_group('Logging options')
    logging_group.set_defaults(log_level=logging.WARNING)
    logging_group.add_argument('-d', '--debug', dest='log_level', action='store_const', const=logging.DEBUG, help="show debug messages")
    logging_group.add_argument('-v', '--verbose', dest='log_level', action='store_const', const=logging.INFO, help="show verbose messages")
    logging_group.add_argument('-q', '--quiet', dest='log_level', action='store_const', const=logging.ERROR, help="show only errors")
    logging_group.add_argument('-Q', '--silent', dest='log_level', action='store_const', const=logging.CRITICAL, help="show nothing")
    logging_group.add_argument('--log', default=None, help="log file")

# %% ../blog/posts/multilabel2/multilabel2.ipynb 24
import sys
import os
from contextlib import contextmanager
from functools import partial

@contextmanager
def redirect(fileno, target):
	""" Redirect a file descriptor temporarily """
	target_fd = os.open(target, os.O_WRONLY)
	saved_fd = os.dup(fileno)
	os.dup2(target_fd, fileno)
	try:
		yield
	finally:
		os.dup2(saved_fd, fileno)
		os.close(saved_fd)
		os.close(target_fd)

redirect_stderr_to_dev_null = partial(redirect, sys.stderr.fileno(), "/dev/null")

# %% ../blog/posts/multilabel2/multilabel2.ipynb 27
from nbdev.export import nb_export
import ipynbname
from pathlib import Path
import sh

def git_root():
    root = sh.git('rev-parse', '--show-toplevel').rstrip()
    return root

def export(nb_file=None, lib_dir=None):
    if nb_file is None: nb_file = ipynbname.name() + '.ipynb'
    if lib_dir is None: lib_dir = Path(git_root())/"lib"
    nb_export(nb_file, lib_dir)
