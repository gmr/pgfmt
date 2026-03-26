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

        keywords = self._collect_select_keywords(node)
        width = max(len(k) for k in keywords)
        lines = []

        distinct = ''
        if node.get('distinctClause') is not None:
            distinct = 'DISTINCT '
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
            for kw, content, quals in from_items:
                lines.append(self._river_line(kw, content, width))
                if quals is not None:
                    self._format_condition_clause('ON', quals, width, lines)

        where = node.get('whereClause')
        if where:
            self._format_condition_clause('WHERE', where, width, lines)

        group = node.get('groupClause')
        if group:
            exprs = ', '.join(self.deparse(g) for g in group)
            lines.append(self._river_line('GROUP BY', exprs, width))

        having = node.get('havingClause')
        if having:
            self._format_condition_clause('HAVING', having, width, lines)

        sort = node.get('sortClause')
        if sort:
            exprs = ', '.join(self.deparse(s) for s in sort)
            lines.append(self._river_line('ORDER BY', exprs, width))

        limit = node.get('limitCount')
        if limit:
            lines.append(self._river_line('LIMIT', self.deparse(limit), width))

        offset = node.get('limitOffset')
        if offset:
            lines.append(
                self._river_line('OFFSET', self.deparse(offset), width)
            )

        return '\n'.join(f'{prefix}{line}' for line in lines)

    def format_insert(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'], include_alias=False
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
            self._append_comma_list('VALUES', rows, width, lines)
        else:
            inner = self.format_select(select, indent=width + 1)
            lines.append(inner)

        return '\n'.join(lines)

    def format_update(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'], include_alias=False
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
            self._format_condition_clause('WHERE', where, width, lines)

        return '\n'.join(lines)

    def format_delete(self, node: dict) -> str:
        relation = self._deparse_range_var(
            node['relation'], include_alias=False
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
            self._format_condition_clause('WHERE', where, width, lines)

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # River formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _river_line(keyword: str, content: str, width: int) -> str:
        if content:
            return f'{keyword:>{width}} {content}'
        return f'{keyword:>{width}}'

    def _append_comma_list(
        self,
        keyword: str,
        items: list[str],
        width: int,
        lines: list[str],
    ) -> None:
        """Append a keyword + comma-separated items with continuation."""
        first = items[0]
        if len(items) > 1:
            first += ','
        lines.append(self._river_line(keyword, first, width))
        content_indent = ' ' * (width + 1)
        for i, item in enumerate(items[1:], 1):
            suffix = ',' if i < len(items) - 1 else ''
            lines.append(f'{content_indent}{item}{suffix}')

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
        if 'JoinExpr' in node:
            join = node['JoinExpr']
            keywords.append(self._join_keyword(join))
            keywords.append('ON')
            quals = join.get('quals')
            if quals:
                self._collect_condition_keywords(quals, keywords)
            self._collect_join_keywords(join['larg'], keywords)
            if 'JoinExpr' in join.get('rarg', {}):
                self._collect_join_keywords(join['rarg'], keywords)

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

    def _flatten_from(
        self,
        from_clause: list[dict],
    ) -> list[tuple[str, str, dict | None]]:
        items: list[tuple[str, str, dict | None]] = []
        for node in from_clause:
            self._flatten_from_node(node, items, is_first=not items)
        return items

    def _flatten_from_node(
        self,
        node: dict,
        items: list[tuple[str, str, dict | None]],
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
            items.append((kw, right, quals))
        else:
            items.append(('FROM', self.deparse(node), None))

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
