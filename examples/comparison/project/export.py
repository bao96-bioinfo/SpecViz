"""Intentionally contradicts the requested password-protection example."""


def create_export(password=None):
    if password is not None:
        raise ValueError("Password protection unavailable")
    return "report.csv"
