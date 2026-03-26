import argparse
import sys

import pgfmt


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Format PostgreSQL SQL statements'
    )
    parser.add_argument(
        'files',
        nargs='*',
        type=argparse.FileType('r'),
        help='SQL files to format (reads stdin if none given)',
    )
    parser.add_argument(
        '--style',
        default='river',
        choices=['river', 'mozilla', 'aweber'],
        help='formatting style (default: river)',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='check if files are already formatted (exit 1 if not)',
    )
    args = parser.parse_args()

    sources = args.files or [sys.stdin]
    exit_code = 0

    for source in sources:
        sql = source.read()
        if not sql.strip():
            continue
        formatted = pgfmt.format(sql, style=args.style)
        if args.check:
            if formatted.strip() != sql.strip():
                name = getattr(source, 'name', '<stdin>')
                sys.stderr.write(f'Would reformat: {name}\n')
                exit_code = 1
        else:
            sys.stdout.write(formatted)

    raise SystemExit(exit_code)
