import pgfmt.river


class AWeberFormatter(pgfmt.river.RiverFormatter):
    """Format SQL using the AWeber style.

    Based on the river style with JOINs as river keywords.
    INNER JOIN, LEFT JOIN, etc. participate in the river
    alignment alongside SELECT, FROM, WHERE, and ON/AND.
    """

    def format_select(
        self,
        node: dict,
        indent: int = 0,
        min_width: int = 0,
    ) -> str:
        with_clause = node.get('withClause')
        if with_clause and min_width == 0:
            width = self._unified_river_width(node)
            return super().format_select(
                node,
                indent,
                min_width=width,
            )
        return super().format_select(
            node,
            indent,
            min_width=min_width,
        )

    def _unified_river_width(self, node: dict) -> int:
        """Compute the max river width across CTEs + outer query."""
        all_keywords = list(self._collect_select_keywords(node))
        with_clause = node.get('withClause')
        if with_clause:
            for cte_node in with_clause.get('ctes', []):
                cte = cte_node['CommonTableExpr']
                query = cte['ctequery']
                inner = query.get('SelectStmt', query)
                all_keywords.extend(self._collect_select_keywords(inner))
        return max(len(k) for k in all_keywords)

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
