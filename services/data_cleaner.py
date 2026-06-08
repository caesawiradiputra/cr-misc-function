"""Data cleaning utilities for string manipulation and normalization."""


def strip_leading_spaces(value: str | None) -> str | None:
    """
    Strip leading whitespace from a string.

    Args:
        value: The string to clean, or None.

    Returns:
        The string with leading spaces removed, or None if input is None.

    Example:
        >>> strip_leading_spaces("  hello world")
        "hello world"
        >>> strip_leading_spaces(None)
        None
    """
    if value is None:
        return None
    return value.lstrip()


def strip_leading_spaces_batch(values: list[str | None]) -> list[str | None]:
    """
    Strip leading whitespace from a list of strings.

    Args:
        values: List of strings to clean (can include None values).

    Returns:
        List of cleaned strings with leading spaces removed.

    Example:
        >>> strip_leading_spaces_batch(["  foo", "  bar", None])
        ["foo", "bar", None]
    """
    return [strip_leading_spaces(v) for v in values]
