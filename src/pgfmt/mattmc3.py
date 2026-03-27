import pgfmt.aweber


class Mattmc3Formatter(pgfmt.aweber.AWeberFormatter):
    """Format SQL using the mattmc3 "Modern SQL Style".

    A lowercase river-style formatter with leading commas.
    Based on the AWeber style (JOINs as river keywords) with:
    - Lowercase keywords
    - Leading commas instead of trailing
    - Plain ``join`` preferred over ``inner join``
    """

    def _kw(self, keyword: str) -> str:
        """Return keyword in lowercase."""
        return keyword.lower()

    def _is_plain_join(self, node: dict) -> bool:
        """Always use plain JOIN, never INNER JOIN."""
        return True

    # ------------------------------------------------------------------
    # Leading comma support
    # ------------------------------------------------------------------

    def _append_comma_list(
        self,
        keyword: str,
        items: list[str],
        width: int,
        lines: list[str],
    ) -> None:
        """Append keyword + items using leading commas."""
        if not items:
            return
        lines.append(self._river_line(keyword, items[0], width))
        pad = ' ' * (width - 1)
        for item in items[1:]:
            self._append_leading_comma_item(
                item,
                pad,
                lines,
            )

    @staticmethod
    def _append_leading_comma_item(
        item: str,
        pad: str,
        lines: list[str],
    ) -> None:
        """Append a single item with a leading comma prefix."""
        if '\n' not in item:
            lines.append(f'{pad}, {item}')
            return
        sub_lines = item.split('\n')
        lines.append(f'{pad}, {sub_lines[0]}')
        content_pad = ' ' * (len(pad) + 2)
        for sub_line in sub_lines[1:]:
            lines.append(f'{content_pad}{sub_line}')

    # ------------------------------------------------------------------
    # Override format methods for lowercase keywords
    # ------------------------------------------------------------------

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
            'select',
            [first_target, *targets[1:]],
            width,
            lines,
        )

        from_clause = node.get('fromClause', [])
        if from_clause:
            self._format_from_items(from_clause, width, lines)

        self._format_trailing(node, width, lines)

        raw = '\n'.join(lines)
        body = '\n'.join(f'{prefix}{line}' for line in raw.split('\n'))
        if cte_lines:
            return f'{cte_lines}\n{body}'
        return body

    def _format_from_items(
        self,
        from_clause: list,
        width: int,
        lines: list[str],
    ) -> None:
        from_items = self._flatten_from(from_clause)
        content_pad = ' ' * (width + 1)
        for _idx, (kw, table, quals, using, is_qual) in enumerate(
            from_items,
        ):
            kw_lower = kw.lower() if kw != ',' else kw
            if not is_qual:
                self._format_river_from_item(
                    kw,
                    kw_lower,
                    table,
                    quals,
                    using,
                    width,
                    content_pad,
                    lines,
                )
            else:
                if _idx > 1:
                    lines.append('')
                lines.append(f'{content_pad}{kw_lower} {table}')
                if quals is not None:
                    self._format_join_on(
                        quals,
                        content_pad,
                        lines,
                    )
                if using is not None:
                    cols = ', '.join(self._extract_names(using))
                    lines.append(f'{content_pad}using ({cols})')

    def _format_river_from_item(
        self,
        kw: str,
        kw_lower: str,
        table: str,
        quals: dict | None,
        using: list | None,
        width: int,
        content_pad: str,
        lines: list[str],
    ) -> None:
        if kw == ',':
            lines[-1] += ','
            lines.append(f'{content_pad}{table}')
        else:
            lines.append(
                self._river_line(kw_lower, table, width),
            )
        if quals is not None:
            self._format_condition_clause(
                'on',
                quals,
                width,
                lines,
            )
        if using is not None:
            cols = ', '.join(self._extract_names(using))
            lines.append(
                self._river_line('using', f'({cols})', width),
            )

    def _format_trailing(
        self,
        node: dict,
        width: int,
        lines: list[str],
    ) -> None:
        where = node.get('whereClause')
        if where:
            self._format_condition_clause(
                'where',
                where,
                width,
                lines,
            )
        group = node.get('groupClause')
        if group:
            exprs = ', '.join(self.deparse(g) for g in group)
            lines.append(self._river_line('group by', exprs, width))
        having = node.get('havingClause')
        if having:
            self._format_condition_clause(
                'having',
                having,
                width,
                lines,
            )
        sort = node.get('sortClause')
        if sort:
            exprs = ', '.join(self.deparse(s) for s in sort)
            lines.append(self._river_line('order by', exprs, width))
        limit = node.get('limitCount')
        if limit:
            lines.append(
                self._river_line(
                    'limit',
                    self.deparse(limit),
                    width,
                )
            )
        offset = node.get('limitOffset')
        if offset:
            lines.append(
                self._river_line(
                    'offset',
                    self.deparse(offset),
                    width,
                )
            )

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

        keywords = ['insert into']
        values_lists = select.get('valuesLists')
        if values_lists:
            keywords.append('values')
        width = max(len(k) for k in keywords)

        lines = []
        lines.append(
            self._river_line(
                'insert into',
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
                'values',
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
        from_clause = node.get('fromClause', [])

        keywords = ['update', 'set']
        if from_clause:
            keywords.append('from')
            for item in from_clause:
                self._collect_join_keywords(item, keywords)
        if where:
            keywords.append('where')
            self._collect_condition_keywords(where, keywords)
        width = max(len(k) for k in keywords)

        lines = []
        lines.append(self._river_line('update', relation, width))

        set_items = []
        for t in targets:
            rt = t['ResTarget']
            set_items.append(
                f'{rt["name"]} = {self.deparse(rt.get("val"))}',
            )
        self._append_comma_list('set', set_items, width, lines)

        if from_clause:
            self._format_from_items(from_clause, width, lines)

        if where:
            self._format_condition_clause(
                'where',
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

        keywords = ['delete', 'from']
        if where:
            keywords.append('where')
            self._collect_condition_keywords(where, keywords)
        width = max(len(k) for k in keywords)

        lines = []
        lines.append(self._river_line('delete', '', width))
        lines.append(self._river_line('from', relation, width))

        if where:
            self._format_condition_clause(
                'where',
                where,
                width,
                lines,
            )

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Override helpers for lowercase keywords
    # ------------------------------------------------------------------

    def _collect_select_keywords(self, node: dict) -> list[str]:
        keywords = ['select']
        from_clause = node.get('fromClause', [])
        if from_clause:
            keywords.append('from')
            for item in from_clause:
                self._collect_join_keywords(item, keywords)
        where = node.get('whereClause')
        if where:
            keywords.append('where')
            self._collect_condition_keywords(where, keywords)
        if node.get('groupClause'):
            keywords.append('group by')
        having = node.get('havingClause')
        if having:
            keywords.append('having')
            self._collect_condition_keywords(having, keywords)
        if node.get('sortClause'):
            keywords.append('order by')
        if node.get('limitCount'):
            keywords.append('limit')
        if node.get('limitOffset'):
            keywords.append('offset')
        return keywords

    def _collect_join_keywords(
        self,
        node: dict,
        keywords: list[str],
    ) -> None:
        if 'JoinExpr' not in node:
            return
        join = node['JoinExpr']
        kw = self._join_keyword(join)
        keywords.append(kw.lower() if kw != ',' else kw)
        if join.get('quals') is not None:
            keywords.append('on')
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

    @staticmethod
    def _collect_condition_keywords(
        node: dict,
        keywords: list[str],
    ) -> None:
        if 'BoolExpr' in node:
            boolop = node['BoolExpr']['boolop']
            if boolop == 'AND_EXPR':
                keywords.append('and')
            elif boolop == 'OR_EXPR':
                keywords.append('or')

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
                op_kw = 'and' if boolop == 'AND_EXPR' else 'or'
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
            kw = 'with' if i == 0 else ''
            comma = ',' if i < len(ctes) - 1 else ''
            if kw:
                parts.append(
                    f'{prefix}{kw} {name} as (\n{inner}\n{prefix}){comma}'
                )
            else:
                parts.append(f'{prefix}{name} as (\n{inner}\n{prefix}){comma}')
        return '\n'.join(parts)

    @staticmethod
    def _set_op_keyword(node: dict) -> str:
        op = node.get('op', 'SETOP_NONE')
        is_all = node.get('all', False)
        match op:
            case 'SETOP_UNION':
                base = 'union'
            case 'SETOP_INTERSECT':
                base = 'intersect'
            case 'SETOP_EXCEPT':
                base = 'except'
            case _:
                return ''
        if is_all:
            return f'{base} all'
        return base

    def _format_join_on(self, quals, pad, lines):
        """Format ON/AND for a qualified join (lowercase)."""
        if 'BoolExpr' in quals:
            bool_expr = quals['BoolExpr']
            boolop = bool_expr['boolop']
            if boolop in ('AND_EXPR', 'OR_EXPR'):
                op_kw = 'and' if boolop == 'AND_EXPR' else 'or'
                args = self._flatten_bool_expr(
                    quals,
                    boolop,
                )
                lines.append(f'{pad}on {self.deparse(args[0])}')
                on_pad = pad + '   '
                for arg in args[1:]:
                    lines.append(
                        f'{on_pad}{op_kw} {self.deparse(arg)}',
                    )
                return
        lines.append(f'{pad}on {self.deparse(quals)}')
