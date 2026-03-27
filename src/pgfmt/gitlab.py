import pgfmt.mozilla

INDENT = '  '


class GitLabFormatter(pgfmt.mozilla.MozillaFormatter):
    """Format SQL using the GitLab style.

    Based on the Mozilla style with uppercase keywords, 2-space
    indentation, explicit join types, and CTEs formatted with
    blank lines inside the body.
    """

    def _is_plain_join(self, node: dict) -> bool:
        """Always use explicit INNER JOIN in GitLab style."""
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

        self._gl_format_ctes(node, lines)
        self._gl_format_targets(node, lines)
        self._gl_format_from(node, lines)
        self._gl_format_where(node, lines)
        self._gl_format_group_having(node, lines)
        self._gl_format_order(node, lines)
        self._gl_format_limit_offset(node, lines)

        return '\n'.join(f'{pad}{line}' for line in lines)

    def _gl_format_ctes(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        with_clause = node.get('withClause')
        if not with_clause:
            return
        for i, cte_node in enumerate(with_clause.get('ctes', [])):
            cte = cte_node['CommonTableExpr']
            name = cte['ctename']
            query = cte['ctequery']
            inner = self._format_statement(query)
            kw = self._kw('WITH') if i == 0 else ''
            sep = ',' if i < len(with_clause['ctes']) - 1 else ''
            as_kw = self._kw('AS')
            if kw:
                lines.append(f'{kw} {name} {as_kw} (')
            else:
                lines.append(f'{name} {as_kw} (')
            lines.append('')
            for sub in inner.split('\n'):
                lines.append(f'{INDENT}{sub}')
            lines.append('')
            lines.append(f'){sep}')
            if sep:
                lines.append('')
        lines.append('')

    def _gl_format_targets(
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

    def _gl_format_from(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        from_clause = node.get('fromClause', [])
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

    def _gl_format_where(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        where = node.get('whereClause')
        if where:
            self._format_where(where, lines)

    def _gl_format_group_having(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        group = node.get('groupClause')
        if group:
            group_kw = self._kw('GROUP BY')
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
            self._format_having(having, lines)

    def _gl_format_order(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        sort = node.get('sortClause')
        if not sort:
            return
        order_kw = self._kw('ORDER BY')
        if len(sort) == 1:
            lines.append(f'{order_kw} {self.deparse(sort[0])}')
        else:
            lines.append(order_kw)
            for i, s in enumerate(sort):
                suffix = ',' if i < len(sort) - 1 else ''
                lines.append(
                    f'{INDENT}{self.deparse(s)}{suffix}',
                )

    def _gl_format_limit_offset(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
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

    def format_view(self, node: dict) -> str:
        view = node['view']
        name = self._deparse_range_var(
            view,
            include_alias=False,
        )
        query = node['query']
        inner = self._format_statement(query)
        return f'{self._kw("CREATE VIEW")} {name} {self._kw("AS")}\n{inner}'

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
                op = self._get_operator(
                    node.get('operName', []),
                )
                if op == '=':
                    return f'{test} {self._kw("IN")} (\n{inner}\n{close})'
                return f'{test} {op} {self._kw("ANY")} (\n{inner}\n{close})'
            case 'ALL_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                op = self._get_operator(
                    node.get('operName', []),
                )
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

    def _format_where(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        if 'BoolExpr' in node:
            bool_expr = node['BoolExpr']
            boolop = bool_expr['boolop']
            if boolop in ('AND_EXPR', 'OR_EXPR'):
                op_kw = self._kw(
                    'AND' if boolop == 'AND_EXPR' else 'OR',
                )
                args = self._flatten_bool_expr(node, boolop)
                lines.append(self._kw('WHERE'))
                self._append_indented(
                    self.deparse(args[0]),
                    lines,
                )
                for arg in args[1:]:
                    self._append_indented(
                        f'{op_kw} {self.deparse(arg)}',
                        lines,
                    )
                return
        lines.append(self._kw('WHERE'))
        self._append_indented(self.deparse(node), lines)

    def _format_having(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        lines.append(self._kw('HAVING'))
        self._append_indented(self.deparse(node), lines)

    def _format_on(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        if 'BoolExpr' in node:
            bool_expr = node['BoolExpr']
            boolop = bool_expr['boolop']
            if boolop in ('AND_EXPR', 'OR_EXPR'):
                op_kw = self._kw(
                    'AND' if boolop == 'AND_EXPR' else 'OR',
                )
                args = self._flatten_bool_expr(node, boolop)
                self._append_indented(
                    f'{self._kw("ON")} {self.deparse(args[0])}',
                    lines,
                )
                for arg in args[1:]:
                    self._append_indented(
                        f'{op_kw} {self.deparse(arg)}',
                        lines,
                    )
                return
        self._append_indented(
            f'{self._kw("ON")} {self.deparse(node)}',
            lines,
        )
