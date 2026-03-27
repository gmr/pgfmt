import pgfmt.mozilla

INDENT = '  '


class KickstarterFormatter(pgfmt.mozilla.MozillaFormatter):
    """Format SQL using the Kickstarter style.

    Mozilla-like with 2-space indentation, JOIN + ON on the same
    line, additional join conditions indented below, and compact
    CTE chaining where `), name AS (` appears on one line.
    """

    def _is_plain_join(self, node: dict) -> bool:
        """Always use explicit INNER JOIN."""
        return False

    def format_select(self, node: dict, indent: int = 0) -> str:
        pad = ' ' * indent

        op = node.get('op', 'SETOP_NONE')
        if op != 'SETOP_NONE':
            set_op = self._set_op_keyword(node)
            left = self.format_select(node['larg'], indent)
            right = self.format_select(node['rarg'], indent)
            return f'{left}\n{pad}{set_op}\n{right}'

        lines: list[str] = []

        self._format_cte_compact(node.get('withClause'), lines)
        self._format_select_targets(node, lines)
        self._format_from_clause(node.get('fromClause', []), lines)
        self._format_trailing_clauses(node, lines)

        return '\n'.join(f'{pad}{line}' for line in lines)

    def _format_cte_compact(
        self,
        with_clause: dict | None,
        lines: list[str],
    ) -> None:
        """Format CTEs with compact chaining: `), name AS (`."""
        if not with_clause:
            return
        ctes = with_clause.get('ctes', [])
        for i, cte_node in enumerate(ctes):
            cte = cte_node['CommonTableExpr']
            name = cte['ctename']
            query = cte['ctequery']
            inner = self._format_statement(query)
            as_kw = self._kw('AS')
            if i == 0:
                kw = self._kw('WITH')
                lines.append(f'{kw} {name} {as_kw} (')
            else:
                lines.append(f'), {name} {as_kw} (')
            for sub in inner.split('\n'):
                lines.append(f'{INDENT}{sub}')
        lines.append(')')

    def _format_select_targets(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        """Format the SELECT keyword and target list."""
        distinct = self._format_distinct(
            node.get('distinctClause'),
        )
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

    def _format_from_clause(
        self,
        from_clause: list[dict],
        lines: list[str],
    ) -> None:
        """Format the FROM clause with inline JOIN ... ON."""
        if not from_clause:
            return
        from_kw = self._kw('FROM')
        from_items = self._flatten_from(from_clause)
        for kw, table, quals, using in from_items:
            if kw == ',':
                lines[-1] += ','
                lines.append(f'{INDENT}{table}')
            elif kw == from_kw:
                lines.append(f'{from_kw} {table}')
            else:
                self._format_join_item(
                    kw,
                    table,
                    quals,
                    using,
                    lines,
                )
                continue
            self._format_item_clauses(quals, using, lines)

    def _format_join_item(
        self,
        kw: str,
        table: str,
        quals: dict | None,
        using: list | None,
        lines: list[str],
    ) -> None:
        """Format a single JOIN item with ON on the same line."""
        if quals is not None:
            self._format_join_on_same_line(
                kw,
                table,
                quals,
                lines,
            )
        else:
            lines.append(f'{kw} {table}')
        if using is not None:
            cols = ', '.join(self._extract_names(using))
            lines.append(
                f'{INDENT}{self._kw("USING")} ({cols})',
            )

    def _format_item_clauses(
        self,
        quals: dict | None,
        using: list | None,
        lines: list[str],
    ) -> None:
        """Format ON/USING for non-JOIN from items."""
        if quals is not None:
            self._format_on(quals, lines)
        if using is not None:
            cols = ', '.join(self._extract_names(using))
            lines.append(
                f'{INDENT}{self._kw("USING")} ({cols})',
            )

    def _format_trailing_clauses(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        """Format WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET."""
        where = node.get('whereClause')
        if where:
            self._format_where(where, lines)

        self._format_keyword_list(
            'GROUP BY',
            node.get('groupClause'),
            lines,
        )

        having = node.get('havingClause')
        if having:
            self._format_having(having, lines)

        self._format_keyword_list(
            'ORDER BY',
            node.get('sortClause'),
            lines,
        )

        limit = node.get('limitCount')
        if limit:
            lines.append(
                f'{self._kw("LIMIT")} {self.deparse(limit)}',
            )

        offset = node.get('limitOffset')
        if offset:
            lines.append(
                f'{self._kw("OFFSET")} {self.deparse(offset)}',
            )

    def _format_keyword_list(
        self,
        keyword: str,
        items: list | None,
        lines: list[str],
    ) -> None:
        """Format a keyword followed by a comma-separated list."""
        if not items:
            return
        kw = self._kw(keyword)
        if len(items) == 1:
            lines.append(f'{kw} {self.deparse(items[0])}')
        else:
            lines.append(kw)
            for i, item in enumerate(items):
                suffix = ',' if i < len(items) - 1 else ''
                lines.append(
                    f'{INDENT}{self.deparse(item)}{suffix}',
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
            if len(rows) == 1:
                lines.append(f'{values_kw} {rows[0]}')
            else:
                lines.append(values_kw)
                for i, row in enumerate(rows):
                    suffix = ',' if i < len(rows) - 1 else ''
                    lines.append(f'{INDENT}{row}{suffix}')
        else:
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
        if len(set_items) == 1:
            lines.append(f'{set_kw} {set_items[0]}')
        else:
            lines.append(set_kw)
            for i, item in enumerate(set_items):
                suffix = ',' if i < len(set_items) - 1 else ''
                lines.append(f'{INDENT}{item}{suffix}')

        if where:
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
            self._format_where(where, lines)

        return '\n'.join(lines)

    def format_create_table(
        self,
        node: dict,
        *,
        foreign_server: str | None = None,
        foreign_options: list | None = None,
    ) -> str:
        relation = node['relation']
        name = self._deparse_range_var(
            relation,
            include_alias=False,
        )
        elts = node.get('tableElts', [])
        options = node.get('options')
        prefix = (
            self._kw('CREATE FOREIGN TABLE')
            if foreign_server
            else self._kw('CREATE TABLE')
        )

        lines = [f'{prefix} {name} (']
        for i, elt in enumerate(elts):
            item = self.deparse(elt)
            suffix = ',' if i < len(elts) - 1 else ''
            lines.append(f'{INDENT}{item}{suffix}')
        lines.append(')')

        if options:
            opts = self._deparse_storage_options(options)
            lines[-1] += f'\nWITH ({opts})'

        if foreign_server:
            lines.append(f'SERVER {foreign_server}')

        if foreign_options:
            opt_lines = self._format_foreign_options(
                foreign_options,
                INDENT,
            )
            lines.append(f'OPTIONS (\n{opt_lines}\n)')

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Subquery formatting
    # ------------------------------------------------------------------

    def _deparse_sub_link(self, node: dict) -> str:
        sub_type = node.get('subLinkType', '')
        subselect = node['subselect']
        inner_node = subselect.get('SelectStmt', subselect)
        inner = self.format_select(
            inner_node,
            indent=len(INDENT),
        )

        close = ''
        match sub_type:
            case 'EXISTS_SUBLINK':
                return f'{self._kw("EXISTS")} (\n{inner}\n{close})'
            case 'ANY_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                op = self._get_operator(node.get('operName', []))
                if op == '=':
                    return f'{test} {self._kw("IN")} (\n{inner}\n{close})'
                return f'{test} {op} {self._kw("ANY")} (\n{inner}\n{close})'
            case 'ALL_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                op = self._get_operator(node.get('operName', []))
                return f'{test} {op} {self._kw("ALL")} (\n{inner}\n{close})'
            case _:
                return f'(\n{inner}\n{close})'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _append_indented(content: str, lines: list[str]) -> None:
        """Append content with INDENT, handling multi-line."""
        for sub in content.split('\n'):
            lines.append(f'{INDENT}{sub}')

    def _format_join_on_same_line(
        self,
        join_kw: str,
        table: str,
        quals: dict,
        lines: list[str],
    ) -> None:
        """Format JOIN ... ON on one line with AND indented below."""
        if 'BoolExpr' in quals:
            bool_expr = quals['BoolExpr']
            boolop = bool_expr['boolop']
            if boolop in ('AND_EXPR', 'OR_EXPR'):
                op_kw = self._kw(
                    'AND' if boolop == 'AND_EXPR' else 'OR',
                )
                args = self._flatten_bool_expr(quals, boolop)
                on_kw = self._kw('ON')
                lines.append(
                    f'{join_kw} {table} {on_kw} {self.deparse(args[0])}',
                )
                for arg in args[1:]:
                    lines.append(
                        f'{INDENT}{op_kw} {self.deparse(arg)}',
                    )
                return
        on_kw = self._kw('ON')
        lines.append(
            f'{join_kw} {table} {on_kw} {self.deparse(quals)}',
        )
