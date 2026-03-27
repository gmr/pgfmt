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
        case 'mozilla':
            from pgfmt.mozilla import MozillaFormatter

            formatter = MozillaFormatter()
        case 'aweber':
            from pgfmt.aweber import AWeberFormatter

            formatter = AWeberFormatter()
        case 'dbt':
            from pgfmt.dbt import DbtFormatter

            formatter = DbtFormatter()
        case 'kickstarter':
            from pgfmt.kickstarter import KickstarterFormatter

            formatter = KickstarterFormatter()
        case 'gitlab':
            from pgfmt.gitlab import GitLabFormatter

            formatter = GitLabFormatter()
        case _:
            raise ValueError(f'Unsupported style: {style!r}')
    return formatter.format(sql)
