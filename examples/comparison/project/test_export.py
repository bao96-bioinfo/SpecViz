"""Test definition for inspection; the example does not run it."""

from export import create_export


def test_unprotected_export():
    assert create_export() == "report.csv"
