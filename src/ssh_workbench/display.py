"""Show configuration text literally, with nonprinting characters made visible."""

from collections.abc import Iterable


def display_text(value: str) -> str:
    """Make controls visible without interpreting markup or changing records."""
    return "".join(char if char.isprintable() else ascii(char)[1:-1] for char in value)


def display_lines(values: Iterable[str]) -> str:
    return "\n".join(display_text(value) for value in values)
