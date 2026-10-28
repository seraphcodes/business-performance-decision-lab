"""Pytest fixtures. The test data itself, with its hand-worked totals, is in helpers.py."""
import pytest

from src.classify import add_time_columns, classify
from src.load import prepare
from tests.helpers import build_sheets


@pytest.fixture
def sheets():
    return build_sheets()


@pytest.fixture
def prepared(sheets):
    return prepare(sheets)


@pytest.fixture
def classified(prepared):
    return add_time_columns(classify(prepared))
