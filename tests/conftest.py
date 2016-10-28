import pytest


def pytest_addoption(parser):
    parser.addoption("--debuglogs", action="store_true", help="Add debug logs")
