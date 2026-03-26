import pgfmt.formatter


class RiverFormatter(pgfmt.formatter.Formatter):
    """Format SQL using the river style.

    Keywords are right-aligned so their right edges line up,
    creating a visual "river" that separates keywords from content.
    """

    def format_select(self, node: dict, indent: int = 0) -> str:
        prefix = ' ' * indent

        op = node.get('op', 'SETOP_NONE')
        if op != 'SETOP_NONE':
            set_op = self._set_op_keyword(node)
            left = self.format_select(node['larg'], indent)
            right = self.format_select(node['rarg'], indent)
            return f'{left}\n\n{prefix}{set_op}\n\n{right}'

        cte_lines = self._format_with_clause(
            node.get('withClause'),
            indent,
        )

        keywords = self._collect_select_keywords(node)
        width = max(len(k) for k in keywords)
        lines = []

        distinct = self._format_distinct(
            node.get('distinctClause'),
        )
        targets = [self.deparse(t) for t in node.get('targetList', [])]
        first_target = f'{distinct}{targets[0]}' if targets else ''
        self._append_comma_list(
            'SELECT',
            [first_target, *targets[1:]],
            width,
            lines,
        )

        from_clause = node.get('fromClause', [])
        if from_clause:
            from_items = self._flatten_from(from_clause)
            content_pad = ' ' * (width + 1)
            for idx, (kw, table, quals, using, is_qual) in enumerate(
                from_items,
            ):
                if not is_qual:
                    lines.append(self._river_line(kw, table, width))
                    if quals is not None:
                        self._format_condition_clause(
                            'ON',
                            quals,
                            width,
                            lines,
                        )
                    if using is not None:
                        cols = ', '.join(self._extract_names(using))
                        lines.append(
                            self._river_line(
                                'USING',
                                f'({cols})',
                                width,
                            )
                        )
                else:
                    if idx > 1:
                        lines.append('')
                    lines.append(f'{content_pad}{kw} {table}')
                    if quals is not None:
                        self._format_join_on(
                            quals,
                            content_pad,
                            lines,
                        )
                    if using is not None:
                        cols = ', '.join(self._extract_names(using))
                        lines.append(f'{content_pad}USING ({cols})')

        where = node.get('whereClause')
        if where:
            self._format_condition_clause(
                'WHERE',
                where,
                width,
                lines,
            )

        group = node.get('groupClause')
        if group:
            exprs = ', '.join(self.deparse(g) for g in group)
            lines.append(self._river_line('GROUP BY', exprs, width))

        having = node.get('havingClause')
        if having:
            self._format_condition_clause(
                'HAVING',
                having,
                width,
                lines,
            )

        sort = node.get('sortClause')
        if sort:
            exprs = ', '.join(self.deparse(s) for s in sort)
            lines.append(self._river_line('ORDER BY', exprs, width))

        limit = node.get('limitCount')
        if limit:
            lines.append(
                self._river_line(
                    'LIMIT',
                    self.deparse(limit),
                    width,
                )
            )

        offset = node.get('limitOffset')
        if offset:
            lines.append(
                self._river_line(
                    'OFFSET',
                    self.deparse(offset),
                    width,
                )
            )

        raw = '\n'.join(lines)
        body = '\n'.join(f'{prefix}{line}' for line in raw.split('\n'))
        if cte_lines:
            return f'{cte_lines}\n{body}'
        return body

    def format_insert(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'],
            include_alias=False,
        )
        cols = node.get('cols', [])
        select_stmt = node.get('selectStmt', {})
        select = select_stmt.get('SelectStmt', select_stmt)

        col_list = ''
        if cols:
            col_names = ', '.join(c['ResTarget']['name'] for c in cols)
            col_list = f' ({col_names})'

        keywords = ['INSERT INTO']
        values_lists = select.get('valuesLists')
        if values_lists:
            keywords.append('VALUES')
        width = max(len(k) for k in keywords)

        lines = []
        lines.append(
            self._river_line(
                'INSERT INTO',
                f'{relation}{col_list}',
                width,
            )
        )

        if values_lists:
            rows = []
            for vl in values_lists:
                items = vl['List']['items']
                vals = ', '.join(self.deparse(v) for v in items)
                rows.append(f'({vals})')
            self._append_comma_list(
                'VALUES',
                rows,
                width,
                lines,
            )
        else:
            inner = self.format_select(
                select,
                indent=width + 1,
            )
            lines.append(inner)

        return '\n'.join(lines)

    def format_update(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'],
            include_alias=False,
        )
        targets = node.get('targetList', [])
        where = node.get('whereClause')

        keywords = ['UPDATE', 'SET']
        if where:
            keywords.append('WHERE')
            self._collect_condition_keywords(where, keywords)
        width = max(len(k) for k in keywords)

        lines = []
        lines.append(self._river_line('UPDATE', relation, width))

        set_items = []
        for t in targets:
            rt = t['ResTarget']
            set_items.append(f'{rt["name"]} = {self.deparse(rt.get("val"))}')
        self._append_comma_list('SET', set_items, width, lines)

        if where:
            self._format_condition_clause(
                'WHERE',
                where,
                width,
                lines,
            )

        return '\n'.join(lines)

    def format_delete(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'],
            include_alias=False,
        )
        where = node.get('whereClause')

        keywords = ['DELETE', 'FROM']
        if where:
            keywords.append('WHERE')
            self._collect_condition_keywords(where, keywords)
        width = max(len(k) for k in keywords)

        lines = []
        lines.append(self._river_line('DELETE', '', width))
        lines.append(self._river_line('FROM', relation, width))

        if where:
            self._format_condition_clause(
                'WHERE',
                where,
                width,
                lines,
            )

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

        columns = []
        pk_constraints = []
        other_constraints = []
        for elt in elts:
            if 'ColumnDef' in elt:
                columns.append(elt['ColumnDef'])
            elif 'Constraint' in elt:
                c = elt['Constraint']
                if c.get('contype') == 'CONSTR_PRIMARY':
                    pk_constraints.append(c)
                else:
                    other_constraints.append(c)

        max_name = max(
            (len(c['colname']) for c in columns),
            default=0,
        )
        max_type = max(
            (len(self._deparse_type_name(c['typeName'])) for c in columns),
            default=0,
        )
        type_col = max_name + 1
        cons_col = type_col + max_type + 1

        ordered: list[str] = []
        for pk in pk_constraints:
            keys = self._extract_names(pk.get('keys', []))
            ordered.append(f'    PRIMARY KEY ({", ".join(keys)})')
        for col in columns:
            ordered.append(
                self._format_column_aligned(
                    col,
                    type_col,
                    cons_col,
                )
            )
        for cons in other_constraints:
            ordered.extend(self._format_table_constraint(cons, type_col))

        lines = [f'{prefix} {name} (']
        for i, item in enumerate(ordered):
            is_last = i == len(ordered) - 1
            next_is_continuation = not is_last and ordered[
                i + 1
            ].lstrip().startswith('CHECK(')
            if is_last or next_is_continuation:
                lines.append(item)
            else:
                lines.append(f'{item},')
        lines.append(')')

        if options:
            opts = self._deparse_storage_options(options)
            lines[-1] += f'\nWITH ({opts})'

        if foreign_server:
            lines.append(f'SERVER {foreign_server}')

        if foreign_options:
            opt_lines = self._format_foreign_options(
                foreign_options,
                '    ',
            )
            lines.append(f'OPTIONS (\n{opt_lines}\n)')

        return '\n'.join(lines)

    def _format_column_aligned(
        self,
        col: dict,
        type_col: int,
        cons_col: int,
    ) -> str:
        name = col['colname']
        type_name = self._deparse_type_name(col['typeName'])
        parts = []
        for cons in col.get('constraints', []):
            parts.append(self._deparse_column_constraint(cons['Constraint']))
        padded_name = name.ljust(type_col)
        padded_type = type_name.ljust(cons_col - type_col)
        constraints = ' '.join(parts)
        return f'    {padded_name}{padded_type}{constraints}'.rstrip()

    def _format_table_constraint(
        self,
        cons: dict,
        type_col: int,
    ) -> list[str]:
        pad = ' ' * (4 + type_col)
        contype = cons.get('contype', '')
        conname = cons.get('conname')
        result = []
        if conname:
            result.append(f'{pad}CONSTRAINT {conname}')
        match contype:
            case 'CONSTR_CHECK':
                expr = self.deparse(cons.get('raw_expr'))
                result.append(f'{pad}CHECK({expr})')
            case 'CONSTR_UNIQUE':
                keys = self._extract_names(cons.get('keys', []))
                result.append(f'{pad}UNIQUE ({", ".join(keys)})')
            case 'CONSTR_FOREIGN':
                fk_attrs = self._extract_names(cons.get('fk_attrs', []))
                fk = self._deparse_fk_constraint(cons)
                result.append(f'{pad}FOREIGN KEY ({", ".join(fk_attrs)}) {fk}')
            case _:
                result.append(f'{pad}{self._deparse_constraint(cons)}')
        return result

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
        inner = self.format_select(inner_node)

        match sub_type:
            case 'EXISTS_SUBLINK':
                return self._indent_continuation(
                    'EXISTS (',
                    inner,
                    ')',
                )
            case 'ANY_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                return self._indent_continuation(
                    f'{test} IN (',
                    inner,
                    ')',
                )
            case 'ALL_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                op = self._get_operator(node.get('operName', []))
                return self._indent_continuation(
                    f'{test} {op} ALL (',
                    inner,
                    ')',
                )
            case _:
                return self._indent_continuation(
                    '(',
                    inner,
                    ')',
                )

    # ------------------------------------------------------------------
    # CTE and DISTINCT helpers
    # ------------------------------------------------------------------

    def _format_with_clause(
        self,
        with_clause: dict | None,
        indent: int,
    ) -> str:
        if not with_clause:
            return ''
        prefix = ' ' * indent
        ctes = with_clause.get('ctes', [])
        parts = []
        for i, cte_node in enumerate(ctes):
            cte = cte_node['CommonTableExpr']
            name = cte['ctename']
            query = cte['ctequery']
            inner = self._format_statement(query)
            kw = 'WITH' if i == 0 else ''
            comma = ',' if i < len(ctes) - 1 else ''
            if kw:
                parts.append(
                    f'{prefix}{kw} {name} AS (\n{inner}\n{prefix}){comma}'
                )
            else:
                parts.append(f'{prefix}{name} AS (\n{inner}\n{prefix}){comma}')
        return '\n'.join(parts)

    # ------------------------------------------------------------------
    # River formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _river_line(keyword: str, content: str, width: int) -> str:
        if not content:
            return f'{keyword:>{width}}'
        first_prefix = f'{keyword:>{width}} '
        if '\n' not in content:
            return f'{first_prefix}{content}'
        lines = content.split('\n')
        pad = ' ' * (width + 1)
        result = [f'{first_prefix}{lines[0]}']
        for line in lines[1:]:
            result.append(f'{pad}{line}')
        return '\n'.join(result)

    def _append_comma_list(
        self,
        keyword: str,
        items: list[str],
        width: int,
        lines: list[str],
    ) -> None:
        """Append a keyword + comma-separated items."""
        first = items[0]
        if len(items) > 1:
            first += ','
        lines.append(self._river_line(keyword, first, width))
        content_indent = ' ' * (width + 1)
        for i, item in enumerate(items[1:], 1):
            suffix = ',' if i < len(items) - 1 else ''
            self._append_multiline_item(
                item,
                suffix,
                content_indent,
                lines,
            )

    @staticmethod
    def _append_multiline_item(
        item: str,
        suffix: str,
        indent: str,
        lines: list[str],
    ) -> None:
        if '\n' not in item:
            lines.append(f'{indent}{item}{suffix}')
            return
        sub_lines = item.split('\n')
        lines.append(f'{indent}{sub_lines[0]}')
        for sub_line in sub_lines[1:-1]:
            lines.append(f'{indent}{sub_line}')
        lines.append(f'{indent}{sub_lines[-1]}{suffix}')

    def _collect_select_keywords(self, node: dict) -> list[str]:
        keywords = ['SELECT']
        from_clause = node.get('fromClause', [])
        if from_clause:
            keywords.append('FROM')
            for item in from_clause:
                self._collect_join_keywords(item, keywords)
        where = node.get('whereClause')
        if where:
            keywords.append('WHERE')
            self._collect_condition_keywords(where, keywords)
        if node.get('groupClause'):
            keywords.append('GROUP BY')
        having = node.get('havingClause')
        if having:
            keywords.append('HAVING')
            self._collect_condition_keywords(having, keywords)
        if node.get('sortClause'):
            keywords.append('ORDER BY')
        if node.get('limitCount'):
            keywords.append('LIMIT')
        if node.get('limitOffset'):
            keywords.append('OFFSET')
        return keywords

    def _collect_join_keywords(
        self,
        node: dict,
        keywords: list[str],
    ) -> None:
        if 'JoinExpr' not in node:
            return
        join = node['JoinExpr']
        if not self._is_qualified_join(join):
            keywords.append(self._join_keyword(join))
            keywords.append('ON')
        self._collect_join_keywords(join['larg'], keywords)
        if 'JoinExpr' in join.get('rarg', {}):
            self._collect_join_keywords(
                join['rarg'],
                keywords,
            )

    @staticmethod
    def _collect_condition_keywords(
        node: dict,
        keywords: list[str],
    ) -> None:
        if 'BoolExpr' in node:
            boolop = node['BoolExpr']['boolop']
            if boolop == 'AND_EXPR':
                keywords.append('AND')
            elif boolop == 'OR_EXPR':
                keywords.append('OR')

    def _format_condition_clause(
        self,
        keyword: str,
        node: dict,
        width: int,
        lines: list[str],
    ) -> None:
        if 'BoolExpr' in node:
            bool_expr = node['BoolExpr']
            boolop = bool_expr['boolop']
            if boolop in ('AND_EXPR', 'OR_EXPR'):
                op_kw = 'AND' if boolop == 'AND_EXPR' else 'OR'
                args = self._flatten_bool_expr(node, boolop)
                lines.append(
                    self._river_line(
                        keyword,
                        self.deparse(args[0]),
                        width,
                    )
                )
                for arg in args[1:]:
                    lines.append(
                        self._river_line(
                            op_kw,
                            self.deparse(arg),
                            width,
                        )
                    )
                return
        lines.append(self._river_line(keyword, self.deparse(node), width))

    def _flatten_from(self, from_clause):
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
        node,
        items,
        is_first=False,
    ):
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
            qualified = self._is_qualified_join(join)
            items.append((kw, right, quals, using, qualified))
        else:
            items.append(('FROM', self.deparse(node), None, None, False))

    def _is_qualified_join(self, join: dict) -> bool:
        kw = self._join_keyword(join)
        return kw not in ('JOIN', 'NATURAL JOIN')

    def _format_join_on(self, quals, pad, lines):
        """Format ON/AND for a qualified join."""
        if 'BoolExpr' in quals:
            bool_expr = quals['BoolExpr']
            boolop = bool_expr['boolop']
            if boolop in ('AND_EXPR', 'OR_EXPR'):
                op_kw = 'AND' if boolop == 'AND_EXPR' else 'OR'
                args = self._flatten_bool_expr(
                    quals,
                    boolop,
                )
                lines.append(f'{pad}ON {self.deparse(args[0])}')
                on_pad = pad + '   '
                for arg in args[1:]:
                    lines.append(f'{on_pad}{op_kw} {self.deparse(arg)}')
                return
        lines.append(f'{pad}ON {self.deparse(quals)}')

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
