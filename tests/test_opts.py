# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# ruff: noqa: ARG001


"""Test parsing CLI arguments."""


from unittest import mock
from collections.abc import Generator

import pytest

from trelby import opts


def _assert_opts(
        *,
        is_test: bool = False,
        conf: str | None = None,
        filenames: list[str] | None = None
) -> None:
    """Assert that CLI arguments are properly parsed.

    Args:
        is_test: expected value for isTest.
        conf: expected value for conf.
        filenames: expected value for filenames.

    """

    if hasattr(opts, 'isTest'):
        assert opts.isTest is bool(is_test)
    else:
        assert is_test is False

    if conf is None:
        assert getattr(opts, 'conf', None) is None
    else:
        assert isinstance(conf, str)
        assert opts.conf == conf

    if filenames is None:
        assert getattr(opts, 'filenames', []) == []  # pylint:disable=C1803
    else:
        assert isinstance(filenames, list)
        assert opts.filenames == filenames
        for filename in opts.filenames:
            assert isinstance(filename, str)


@pytest.fixture
def reset_opts() -> Generator:
    """Reset parsed CLI arguments.

    Yields:
        Nothing.

    """

    _assert_opts()

    yield

    opts.isTest = False
    opts.conf = None
    opts.filenames = []


def test_parsing_cli_no_args(
        reset_opts: None, subtests: pytest.Subtests
) -> None:
    """Test parsing CLI without arguments."""

    with subtests.test('No CLI arguments.'):
        argv: list[str] = []
        with mock.patch('trelby.opts.sys.argv', argv):
            opts.init()
        _assert_opts()

    with subtests.test('Only program argument.'):
        argv = ['spam.py']
        with mock.patch('trelby.opts.sys.argv', argv):
            opts.init()
        _assert_opts()


def test_parsing_cli_test(reset_opts: None) -> None:
    """Test parsing CLI with just --test."""

    argv = ['spam.py', '--test']
    with mock.patch('trelby.opts.sys.argv', argv):
        opts.init()

    _assert_opts(is_test=True)


def test_parsing_cli_config(reset_opts: None) -> None:
    """Test parsing CLI with --config."""

    argv = ['spam.py', '--conf', 'ham', 'eggs']
    with mock.patch('trelby.opts.sys.argv', argv):
        opts.init()

    _assert_opts(conf='ham', filenames=['eggs'])


def test_parsing_cli_config_without_value(reset_opts: None) -> None:
    """Test parsing CLI with --config without value."""

    argv = ['spam.py', 'eggs', '--conf']
    with mock.patch('trelby.opts.sys.argv', argv):
        opts.init()

    _assert_opts(filenames=['eggs'])


@pytest.mark.parametrize(
    'cli_args', [['ham', ], ['eggs', 'ham'], ['bar', 'foo', 'ham']],
)
def test_parsing_cli_filenames(reset_opts: None, cli_args: list[str]) -> None:
    """Test parsing CLI with only filenames."""

    argv = ['spam.py', *cli_args]
    with mock.patch('trelby.opts.sys.argv', argv):
        opts.init()

    _assert_opts(filenames=cli_args)
