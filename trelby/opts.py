# -*- coding: utf-8 -*-

# ruff: noqa:PLW0603


"""Parse arguments passed from Command-Line-Interpreter."""


import sys
import argparse


def _init() -> None:
    """Parse arguments passed from CLI via `sys.argv` and sets CLI options.

    Currently, CLI options are:

    *   is_test_mode: to run in test mode.
    *   conf: to use the given file as configuration file
            instead of the default one.
    *   filenames: script files to be opened.

    """
    try:
        prog = sys.argv[0]
    except IndexError:
        prog = 'trelby'
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            'Trelby is a screenplay writing program. '
            'See https://www.trelby.org/ for more details.'
        )
    )

    # help information from README.dev file
    parser.add_argument(
        '-t',
        '--test',
        action='store_true',
        dest='is_test_mode',
        help=' run Trelby in test mode'
    )
    # help information from Trelby manual
    # SEE: https://trelby.org/assets/manual.html#cmdparams
    parser.add_argument(
        '-c',
        '--conf',
        # --conf can accept no argument as was coded previously
        nargs='?',
        type=str,
        help=(
            'read global settings from the given file '
            'instead of "default.conf"'
        )
    )
    parser.add_argument(
        'filenames',
        nargs='*',
        help='open the given script files'
    )

    return parser.parse_args(sys.argv[1:])


_opts: argparse.Namespace = _init()


def __getattr__(name: str) -> object:
    """Get the attribute whose name is given.

    Args:
        name: name of the attribute.

    Returns:
        The value of the attribute whose name is given.

    Raises:
        AttributeError: if any attribute with the given name is found.

    """
    if name in ('is_test_mode', 'conf', 'filenames'):
        return getattr(_opts, name)
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}",
        name=name,
        obj=sys.modules[__name__]
    )

# TODO: (jdveiga) investigate test mode --test????
# TODO: (jdveiga) I think that test mode mostly legacy and does nothing.
