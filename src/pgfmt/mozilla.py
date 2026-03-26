import pgfmt.formatter

INDENT = '    '


class MozillaFormatter(pgfmt.formatter.Formatter):
    """Format SQL using the Mozilla style.

    Keywords are left-aligned at column 0 with content indented
    4 spaces underneath.  Each item gets its own line.  AND/OR
    appear at the start of a line under WHERE.
    """

    def format_select(self, node: dict, indent: int = 0) -> str:
        pad = ' ' * indent

        op = node.get('op', 'SETOP_NONE')
        if op != 'SETOP_NONE':
            set_op = self._set_op_keyword(node)
            left = self.format_select(node['larg'], indent)
            right = self.format_select(node['rarg'], indent)
            return f'{left}\n{pad}{set_op}\n{right}'

        lines: list[str] = []

        with_clause = node.get('withClause')
        if with_clause:
            for i, cte_node in enumerate(
                with_clause.get('ctes', []),
            ):
                cte = cte_node['CommonTableExpr']
                name = cte['ctename']
                query = cte['ctequery']
                inner = self._format_statement(query)
                kw = 'WITH' if i == 0 else ''
                sep = ',' if i < len(with_clause['ctes']) - 1 else ''
                if kw:
                    lines.append(f'{kw} {name} AS (')
                else:
                    lines.append(f'{name} AS (')
                for sub in inner.split('\n'):
                    lines.append(f'{INDENT}{sub}')
                lines.append(f'){sep}')
                if not sep:
                    lines.append('')

        distinct = self._format_distinct(
            node.get('distinctClause'),
        )
        targets = [self.deparse(t) for t in node.get('targetList', [])]
        if len(targets) == 1:
            lines.append(f'SELECT {distinct}{targets[0]}')
        else:
            lines.append('SELECT')
            for i, t in enumerate(targets):
                pfx = distinct if i == 0 else ''
                suffix = ',' if i < len(targets) - 1 else ''
                lines.append(f'{INDENT}{pfx}{t}{suffix}')

        from_clause = node.get('fromClause', [])
        if from_clause:
            from_items = self._flatten_from(from_clause)
            for kw, table, quals, using in from_items:
                has_joins = len(from_items) > 1
                if kw == ',':
                    lines[-1] += ','
                    lines.append(f'{INDENT}{table}')
                elif kw == 'FROM' and not has_joins:
                    lines.append(f'FROM {table}')
                elif kw == 'FROM':
                    lines.append('FROM')
                    lines.append(f'{INDENT}{table}')
                else:
                    lines.append(kw)
                    lines.append(f'{INDENT}{table}')
                if quals is not None:
                    self._format_on(quals, lines)
                if using is not None:
                    cols = ', '.join(self._extract_names(using))
                    self._append_indented(
                        f'USING ({cols})',
                        lines,
                    )

        where = node.get('whereClause')
        if where:
            self._format_where(where, lines)

        group = node.get('groupClause')
        if group:
            if len(group) == 1:
                lines.append(f'GROUP BY {self.deparse(group[0])}')
            else:
                lines.append('GROUP BY')
                for i, g in enumerate(group):
                    suffix = ',' if i < len(group) - 1 else ''
                    lines.append(f'{INDENT}{self.deparse(g)}{suffix}')

        having = node.get('havingClause')
        if having:
            self._format_having(having, lines)

        sort = node.get('sortClause')
        if sort:
            if len(sort) == 1:
                lines.append(f'ORDER BY {self.deparse(sort[0])}')
            else:
                lines.append('ORDER BY')
                for i, s in enumerate(sort):
                    suffix = ',' if i < len(sort) - 1 else ''
                    lines.append(f'{INDENT}{self.deparse(s)}{suffix}')

        limit = node.get('limitCount')
        if limit:
            lines.append(f'LIMIT {self.deparse(limit)}')

        offset = node.get('limitOffset')
        if offset:
            lines.append(f'OFFSET {self.deparse(offset)}')

        return '\n'.join(f'{pad}{line}' for line in lines)

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

        lines.append(f'INSERT INTO {relation}{col_list}')

        values_lists = select.get('valuesLists')
        if values_lists:
            rows = []
            for vl in values_lists:
                items = vl['List']['items']
                vals = ', '.join(self.deparse(v) for v in items)
                rows.append(f'({vals})')
            if len(rows) == 1:
                lines.append(f'VALUES {rows[0]}')
            else:
                lines.append('VALUES')
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
        lines.append(f'UPDATE {relation}')

        set_items = []
        for t in targets:
            rt = t['ResTarget']
            set_items.append(f'{rt["name"]} = {self.deparse(rt.get("val"))}')
        if len(set_items) == 1:
            lines.append(f'SET {set_items[0]}')
        else:
            lines.append('SET')
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
        lines.append(f'DELETE FROM {relation}')

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
        prefix = 'CREATE FOREIGN TABLE' if foreign_server else 'CREATE TABLE'

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
        return f'CREATE VIEW {name} AS\n{inner}'

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
                return f'EXISTS (\n{inner}\n{close})'
            case 'ANY_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                op = self._get_operator(node.get('operName', []))
                if op == '=':
                    return f'{test} IN (\n{inner}\n{close})'
                return f'{test} {op} ANY (\n{inner}\n{close})'
            case 'ALL_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                op = self._get_operator(node.get('operName', []))
                return f'{test} {op} ALL (\n{inner}\n{close})'
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
                op_kw = 'AND' if boolop == 'AND_EXPR' else 'OR'
                args = self._flatten_bool_expr(node, boolop)
                lines.append('WHERE')
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
        lines.append('WHERE')
        self._append_indented(self.deparse(node), lines)

    def _format_having(
        self,
        node: dict,
        lines: list[str],
    ) -> None:
        lines.append('HAVING')
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
                op_kw = 'AND' if boolop == 'AND_EXPR' else 'OR'
                args = self._flatten_bool_expr(node, boolop)
                self._append_indented(
                    f'ON {self.deparse(args[0])}',
                    lines,
                )
                for arg in args[1:]:
                    self._append_indented(
                        f'{op_kw} {self.deparse(arg)}',
                        lines,
                    )
                return
        self._append_indented(
            f'ON {self.deparse(node)}',
            lines,
        )

    def _flatten_from(
        self,
        from_clause: list[dict],
    ) -> list:
        items = []
        for node in from_clause:
            self._flatten_from_node(
                node,
                items,
                is_first=not items,
            )
        return items

    def _flatten_from_node(
        self,
        node: dict,
        items: list,
        is_first: bool = False,
    ) -> None:
        if 'JoinExpr' in node:
            join = node['JoinExpr']
            self._flatten_from_node(
                join['larg'],
                items,
                is_first=is_first,
            )
            kw = self._join_keyword(join)
            right = self.deparse(join['rarg'])
            quals = join.get('quals')
            using = join.get('usingClause')
            items.append((kw, right, quals, using))
        else:
            kw = 'FROM' if is_first else ','
            items.append((kw, self.deparse(node), None, None))

    @staticmethod
    def _set_op_keyword(node: dict) -> str:
        op = node.get('op', 'SETOP_NONE')
        is_all = node.get('all', False)
        match op:
            case 'SETOP_UNION':
                base = 'UNION'
            case 'SETOP_INTERSECT':
                base = 'INTERSECT'
            case 'SETOP_EXCEPT':
                base = 'EXCEPT'
            case _:
                return ''
        if is_all:
            return f'{base} ALL'
        return base
