# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# ruff: noqa: ARG001


"""Test parsing CLI arguments."""


import importlib
import sys
from collections.abc import Generator
from types import ModuleType
from unittest import mock

import pytest


def _assert_opts(
        opts: ModuleType,
        *,
        is_test: bool = False,
        conf: str | None = None,
        filenames: list[str] | None = None
) -> None:
    """Assert that CLI arguments are properly parsed.

    Args:
        opts: `opts` module.
        is_test: expected value for is_test_mode.
        conf: expected value for conf.
        filenames: expected value for filenames.

    """

    assert opts.is_test_mode is bool(is_test)

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
    exists_trelby_opts = 'trelby.opts' in sys.modules

    with (
            mock.patch.dict(
                sys.modules,
                {
                    name: module for name, module in sys.modules.items()
                    if name != 'trelby.opts'
                },
                clear=True
            )
    ):
        assert 'trelby.opts' not in sys.modules
        yield

    assert bool('trelby.opts' in sys.modules) is exists_trelby_opts


def _test_parsing_cli(
        argv: list[str],
        *,
        is_test: bool = False,
        conf: str | None = None,
        filenames: list[str] | None = None
) -> None:
    """Test parsing arguments from CLI.

    Args:
        argv: fake arguments from CLI.
        is_test: expected value for is_test_mode.
        conf: expected value for conf.
        filenames: expected value for filenames.

    """
    with mock.patch.object(sys, 'argv', argv):
        opts = importlib.import_module('.opts', 'trelby')

    assert 'trelby.opts' in sys.modules
    _assert_opts(opts, is_test=is_test, conf=conf, filenames=filenames)


def test_parsing_cli_no_args(
        reset_opts: None, subtests: pytest.Subtests
) -> None:
    """Test parsing CLI without arguments."""

    with subtests.test('No CLI arguments.'):
        _test_parsing_cli([])

    with subtests.test('Only program argument.'):
        _test_parsing_cli(['spam.py'])


@pytest.mark.parametrize('param', ['--test', '-t'])
def test_parsing_cli_test(reset_opts: None, param: str) -> None:
    """Test parsing CLI with just --test."""
    _test_parsing_cli(
        ['spam.py', param],
        is_test=True
    )


@pytest.mark.parametrize('param', ['--conf', '-c'])
def test_parsing_cli_config(reset_opts: None, param: str) -> None:
    """Test parsing CLI with --config."""
    _test_parsing_cli(
        ['spam.py', param, 'ham', 'eggs'],
        conf='ham',
        filenames=['eggs']
    )


@pytest.mark.parametrize('param', ['--conf', '-c'])
def test_parsing_cli_config_without_value(
        reset_opts: None, param: str
) -> None:
    """Test parsing CLI with --config without value."""
    _test_parsing_cli(
        ['spam.py', 'eggs', param],
        filenames=['eggs']
    )


@pytest.mark.parametrize(
    'cli_args', [['ham', ], ['eggs', 'ham'], ['bar', 'foo', 'ham']],
)
def test_parsing_cli_filenames(reset_opts: None, cli_args: list[str]) -> None:
    """Test parsing CLI with only filenames."""
    _test_parsing_cli(
        ['spam.py', *cli_args],
        filenames=cli_args
    )


def test_getting_missing_attribute() -> None:
    """Test getting a missing attribute from `opts` module."""

    with mock.patch.object(sys, 'argv', []):
        opts = importlib.import_module('.opts', 'trelby')
        with (
                pytest.raises(
                    AttributeError,
                    match=r"module\ 'trelby\.opts'\ has\ no\ attribute\ 'ham'"
                ) as raised
        ):
            opts.ham  # noqa:B018  # pylint: disable=pointless-statement

        assert raised.value.name == 'ham'
        assert raised.value.obj == opts
