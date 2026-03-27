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

    def _format_cte_body(
        self,
        inner_node: dict,
        min_width: int,
    ) -> str:
        """Format a CTE body, indenting nested CTEs to the river."""
        nested_with = inner_node.get('withClause')
        if not nested_with or min_width == 0:
            return self.format_select(
                inner_node,
                min_width=min_width,
            )
        with_kw = self._kw('WITH')
        as_kw = self._kw('AS')
        kw_pad = ' ' * (min_width - len(with_kw))
        content_col = min_width + 1
        close_pad = ' ' * content_col
        nested_ctes = nested_with.get('ctes', [])
        parts = []
        for i, cte_node in enumerate(nested_ctes):
            cte = cte_node['CommonTableExpr']
            name = cte['ctename']
            query = cte['ctequery']
            cte_inner = query.get('SelectStmt', query)
            body = self.format_select(
                cte_inner,
                indent=content_col,
            )
            comma = ',' if i < len(nested_ctes) - 1 else ''
            if i == 0:
                parts.append(
                    f'{kw_pad}{with_kw} {name} {as_kw} '
                    f'(\n{body}\n{close_pad}){comma}'
                )
            else:
                parts.append(f'{name} {as_kw} (\n{body}\n{close_pad}){comma}')
        cte_text = '\n'.join(parts)
        stripped = dict(inner_node)
        stripped.pop('withClause', None)
        main_body = self.format_select(
            stripped,
            min_width=min_width,
        )
        return f'{cte_text}\n{main_body}'

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

    def _deparse_case_expr(self, node: dict) -> str:
        case_kw = self._kw('CASE')
        when_kw = self._kw('WHEN')
        then_kw = self._kw('THEN')
        else_kw = self._kw('ELSE')
        end_kw = self._kw('END')

        if 'arg' in node:
            first = f'{case_kw} {self.deparse(node["arg"])} '
            pad = ' ' * len(first)
        else:
            first = f'{case_kw} '
            pad = ' ' * len(first)

        lines = []
        for i, when in enumerate(node.get('args', [])):
            w = when['CaseWhen']
            expr = self.deparse(w['expr'])
            result = self.deparse(w['result'])
            when_prefix = f'{when_kw} {expr} {then_kw} '
            if i == 0:
                line_prefix = f'{first}{when_prefix}'
            else:
                line_prefix = f'{pad}{when_prefix}'
            lines.append(
                self._indent_continuation(
                    line_prefix,
                    result,
                )
            )

        if 'defresult' in node:
            defresult = self.deparse(node['defresult'])
            lines.append(
                self._indent_continuation(
                    f'{pad}{else_kw} ',
                    defresult,
                )
            )

        end_pad = ' ' * (len(case_kw) - len(end_kw))
        lines.append(f'{end_pad}{end_kw}')
        return '\n'.join(lines)

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
