import pgfmt.mozilla

INDENT = '    '


class DbtFormatter(pgfmt.mozilla.MozillaFormatter):
    """Format SQL using the dbt-modern style.

    Based on the Mozilla style but with all lowercase keywords,
    trailing commas, blank lines between clauses, and explicit
    join types.  CTEs use ``with`` on its own line with generous
    whitespace.
    """

    def _kw(self, keyword: str) -> str:
        """Return keyword in lowercase for dbt-modern style."""
        return keyword.lower()

    def _is_plain_join(self, node: dict) -> bool:
        """Always use explicit INNER JOIN in dbt style."""
        return False

    def format_select(self, node: dict, indent: int = 0) -> str:
        pad = ' ' * indent

        op = node.get('op', 'SETOP_NONE')
        if op != 'SETOP_NONE':
            set_op = self._set_op_keyword(node)
            left = self.format_select(node['larg'], indent)
            right = self.format_select(node['rarg'], indent)
            return f'{left}\n\n{pad}{set_op}\n\n{right}'

        lines: list[str] = []

        self._dbt_format_ctes(node, lines)
        self._dbt_format_targets(node, lines)
        self._dbt_format_from(node, lines)
        self._dbt_format_where(node, lines)
        self._dbt_format_group_having(node, lines)
        self._dbt_format_order(node, lines)
        self._dbt_format_limit_offset(node, lines)

        return '\n'.join(f'{pad}{line}' if line else '' for line in lines)

    def _dbt_format_ctes(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        with_clause = node.get('withClause')
        if not with_clause:
            return
        lines.append(self._kw('WITH'))
        for i, cte_node in enumerate(with_clause.get('ctes', [])):
            cte = cte_node['CommonTableExpr']
            name = cte['ctename']
            query = cte['ctequery']
            inner = self._format_statement(query)
            sep = ',' if i < len(with_clause['ctes']) - 1 else ''
            lines.append('')
            lines.append(f'{name} {self._kw("AS")} (')
            lines.append('')
            for sub in inner.split('\n'):
                lines.append(f'{INDENT}{sub}' if sub else '')
            lines.append('')
            lines.append(f'){sep}')
        lines.append('')

    def _dbt_format_targets(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        distinct = self._format_distinct(node.get('distinctClause'))
        targets = [self.deparse(t) for t in node.get('targetList', [])]
        select_kw = self._kw('SELECT')
        if len(targets) == 1:
            lines.append(f'{select_kw} {distinct}{targets[0]}')
        else:
            lines.append(select_kw)
            for i, t in enumerate(targets):
                pfx = distinct if i == 0 else ''
                suffix = ',' if i < len(targets) - 1 else ''
                lines.append(f'{INDENT}{pfx}{t}{suffix}')

    def _dbt_format_from(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        from_clause = node.get('fromClause', [])
        if not from_clause:
            return
        from_kw = self._kw('FROM')
        from_items = self._flatten_from(from_clause)
        lines.append('')
        for kw, table, quals, using in from_items:
            has_joins = len(from_items) > 1
            if kw == ',':
                lines[-1] += ','
                lines.append(f'{INDENT}{table}')
            elif kw == from_kw and not has_joins:
                lines.append(f'{from_kw} {table}')
            elif kw == from_kw:
                lines.append(from_kw)
                lines.append(f'{INDENT}{table}')
            else:
                lines.append(kw)
                lines.append(f'{INDENT}{table}')
            if quals is not None:
                self._format_on(quals, lines)
            if using is not None:
                cols = ', '.join(self._extract_names(using))
                self._append_indented(
                    f'{self._kw("USING")} ({cols})',
                    lines,
                )

    def _dbt_format_where(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        where = node.get('whereClause')
        if where:
            lines.append('')
            self._format_where(where, lines)

    def _dbt_format_group_having(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        group = node.get('groupClause')
        if group:
            group_kw = self._kw('GROUP BY')
            lines.append('')
            if len(group) == 1:
                lines.append(
                    f'{group_kw} {self.deparse(group[0])}',
                )
            else:
                lines.append(group_kw)
                for i, g in enumerate(group):
                    suffix = ',' if i < len(group) - 1 else ''
                    lines.append(
                        f'{INDENT}{self.deparse(g)}{suffix}',
                    )
        having = node.get('havingClause')
        if having:
            lines.append('')
            self._format_having(having, lines)

    def _dbt_format_order(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        sort = node.get('sortClause')
        if not sort:
            return
        order_kw = self._kw('ORDER BY')
        lines.append('')
        if len(sort) == 1:
            lines.append(f'{order_kw} {self.deparse(sort[0])}')
        else:
            lines.append(order_kw)
            for i, s in enumerate(sort):
                suffix = ',' if i < len(sort) - 1 else ''
                lines.append(
                    f'{INDENT}{self.deparse(s)}{suffix}',
                )

    def _dbt_format_limit_offset(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        limit = node.get('limitCount')
        if limit:
            lines.append('')
            lines.append(
                f'{self._kw("LIMIT")} {self.deparse(limit)}',
            )
        offset = node.get('limitOffset')
        if offset:
            lines.append('')
            lines.append(
                f'{self._kw("OFFSET")} {self.deparse(offset)}',
            )

    def format_insert(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'],
            include_alias=False,
        )
        cols = node.get('cols', [])
        select_stmt = node.get('selectStmt', {})
        select = select_stmt.get('SelectStmt', select_stmt)

        lines: list[str] = []

        col_list = ''
        if cols:
            col_names = ', '.join(c['ResTarget']['name'] for c in cols)
            col_list = f' ({col_names})'

        lines.append(
            f'{self._kw("INSERT INTO")} {relation}{col_list}',
        )

        values_lists = select.get('valuesLists')
        if values_lists:
            rows = []
            for vl in values_lists:
                items = vl['List']['items']
                vals = ', '.join(self.deparse(v) for v in items)
                rows.append(f'({vals})')
            values_kw = self._kw('VALUES')
            lines.append('')
            if len(rows) == 1:
                lines.append(f'{values_kw} {rows[0]}')
            else:
                lines.append(values_kw)
                for i, row in enumerate(rows):
                    suffix = ',' if i < len(rows) - 1 else ''
                    lines.append(f'{INDENT}{row}{suffix}')
        else:
            lines.append('')
            inner = self.format_select(select, indent=0)
            lines.append(inner)

        return '\n'.join(lines)

    def format_update(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'],
            include_alias=False,
        )
        targets = node.get('targetList', [])
        where = node.get('whereClause')

        lines: list[str] = []
        lines.append(f'{self._kw("UPDATE")} {relation}')

        set_items = []
        for t in targets:
            rt = t['ResTarget']
            set_items.append(
                f'{rt["name"]} = {self.deparse(rt.get("val"))}',
            )
        set_kw = self._kw('SET')
        lines.append('')
        if len(set_items) == 1:
            lines.append(f'{set_kw} {set_items[0]}')
        else:
            lines.append(set_kw)
            for i, item in enumerate(set_items):
                suffix = ',' if i < len(set_items) - 1 else ''
                lines.append(f'{INDENT}{item}{suffix}')

        if where:
            lines.append('')
            self._format_where(where, lines)

        return '\n'.join(lines)

    def format_delete(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'],
            include_alias=False,
        )
        where = node.get('whereClause')

        lines: list[str] = []
        lines.append(f'{self._kw("DELETE FROM")} {relation}')

        if where:
            lines.append('')
            self._format_where(where, lines)

        return '\n'.join(lines)
