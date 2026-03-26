import pgfmt.river


class AWeberFormatter(pgfmt.river.RiverFormatter):
    """Format SQL using the AWeber style.

    Based on the river style with JOINs as river keywords.
    INNER JOIN, LEFT JOIN, etc. participate in the river
    alignment alongside SELECT, FROM, WHERE, and ON/AND.
    """

    def _is_qualified_join(self, join: dict) -> bool:
        return False

    def _collect_join_keywords(
        self,
        node: dict,
        keywords: list[str],
    ) -> None:
        if 'JoinExpr' not in node:
            return
        join = node['JoinExpr']
        keywords.append(self._join_keyword(join))
        if join.get('quals') is not None:
            keywords.append('ON')
            self._collect_condition_keywords(
                join['quals'],
                keywords,
            )
        self._collect_join_keywords(join['larg'], keywords)
        if 'JoinExpr' in join.get('rarg', {}):
            self._collect_join_keywords(
                join['rarg'],
                keywords,
            )
