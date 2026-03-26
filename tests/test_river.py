import pathlib

import pytest

import pgfmt

FIXTURES = pathlib.Path(__file__).parent / 'fixtures' / 'river'


def _fixture_cases():
    """Yield (name, sql_path, expected_path) for each fixture pair."""
    for sql_file in sorted(FIXTURES.glob('*.sql')):
        expected_file = sql_file.with_suffix('.expected')
        if not expected_file.exists():
            raise FileNotFoundError(
                f'Missing .expected file for {sql_file.name}'
            )
        yield sql_file.stem, sql_file, expected_file


@pytest.fixture(params=list(_fixture_cases()), ids=lambda c: c[0])
def fixture_case(request):
    return request.param


def test_river_format(fixture_case):
    name, sql_path, expected_path = fixture_case
    sql = sql_path.read_text()
    expected = expected_path.read_text().rstrip('\n')
    result = pgfmt.format(sql.strip(), style='river')
    assert result == expected, (
        f'Fixture {name!r} mismatch:\n'
        f'--- expected ---\n{expected}\n'
        f'--- got ---\n{result}'
    )
