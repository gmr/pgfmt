from importlib.metadata import version

__version__ = version('pgfmt')


def format(sql: str, style: str = 'river') -> str:
    """Format SQL string according to the specified style.

    Args:
        sql: The SQL string to format.
        style: The formatting style to use.

    Returns:
        The formatted SQL string.

    Raises:
        ValueError: If the style is not supported.

    """
    match style:
        case 'river':
            from pgfmt.river import RiverFormatter

            formatter = RiverFormatter()
        case _:
            raise ValueError(f'Unsupported style: {style!r}')
    return formatter.format(sql)
