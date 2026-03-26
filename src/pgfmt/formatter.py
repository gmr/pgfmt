import abc

import pgparse

PG_TYPE_MAP = {
    'bool': 'BOOLEAN',
    'int2': 'SMALLINT',
    'int4': 'INTEGER',
    'int8': 'BIGINT',
    'float4': 'REAL',
    'float8': 'DOUBLE PRECISION',
    'numeric': 'NUMERIC',
    'text': 'TEXT',
    'varchar': 'CHARACTER VARYING',
    'bpchar': 'CHARACTER',
    'timestamp': 'TIMESTAMP',
    'timestamptz': 'TIMESTAMP WITH TIME ZONE',
    'date': 'DATE',
    'time': 'TIME',
    'timetz': 'TIME WITH TIME ZONE',
    'interval': 'INTERVAL',
    'uuid': 'UUID',
    'json': 'JSON',
    'jsonb': 'JSONB',
    'bytea': 'BYTEA',
}

_BOOL_TEST_SQL = {
    'IS_TRUE': 'IS TRUE',
    'IS_NOT_TRUE': 'IS NOT TRUE',
    'IS_FALSE': 'IS FALSE',
    'IS_NOT_FALSE': 'IS NOT FALSE',
    'IS_UNKNOWN': 'IS UNKNOWN',
    'IS_NOT_UNKNOWN': 'IS NOT UNKNOWN',
}


class Formatter(abc.ABC):
    """Abstract base class for SQL formatters.

    Subclasses implement statement-level formatting (layout and
    indentation). This base class provides shared AST-to-SQL
    deparsing for individual expression nodes.
    """

    def format(self, sql: str) -> str:
        """Parse and format a SQL string.

        Args:
            sql: One or more SQL statements.

        Returns:
            The formatted SQL string.

        """
        statements = pgparse.parse(sql)
        results = []
        for stmt_wrapper in statements:
            stmt = stmt_wrapper['stmt']
            results.append(self._format_statement(stmt) + ';')
        return '\n\n'.join(results)

    def _format_statement(self, stmt: dict) -> str:
        key = next(iter(stmt))
        node = stmt[key]
        match key:
            case 'SelectStmt':
                return self.format_select(node)
            case 'InsertStmt':
                return self.format_insert(node)
            case 'UpdateStmt':
                return self.format_update(node)
            case 'DeleteStmt':
                return self.format_delete(node)
            case _:
                raise ValueError(f'Unsupported statement type: {key}')

    @abc.abstractmethod
    def format_select(self, node: dict, indent: int = 0) -> str:
        """Format a SELECT statement."""

    @abc.abstractmethod
    def format_insert(self, node: dict) -> str:
        """Format an INSERT statement."""

    @abc.abstractmethod
    def format_update(self, node: dict) -> str:
        """Format an UPDATE statement."""

    @abc.abstractmethod
    def format_delete(self, node: dict) -> str:
        """Format a DELETE statement."""

    # ------------------------------------------------------------------
    # Shared deparsing: AST node -> inline SQL text
    # ------------------------------------------------------------------

    def deparse(self, node: dict | list | None) -> str:
        """Convert any AST node to inline SQL text."""
        if node is None:
            return ''
        if isinstance(node, list):
            return ', '.join(self.deparse(n) for n in node)
        if not isinstance(node, dict):
            return str(node)
        key = next(iter(node))
        value = node[key]
        return self._deparse_node(key, value)

    def _deparse_node(self, node_type: str, node: dict) -> str:
        match node_type:
            case 'ColumnRef':
                return self._deparse_column_ref(node)
            case 'A_Const':
                return self._deparse_a_const(node)
            case 'A_Expr':
                return self._deparse_a_expr(node)
            case 'BoolExpr':
                return self._deparse_bool_expr(node)
            case 'FuncCall':
                return self._deparse_func_call(node)
            case 'TypeCast':
                return self._deparse_type_cast(node)
            case 'NullTest':
                return self._deparse_null_test(node)
            case 'SubLink':
                return self._deparse_sub_link(node)
            case 'CaseExpr':
                return self._deparse_case_expr(node)
            case 'CaseWhen':
                return self._deparse_case_when(node)
            case 'CoalesceExpr':
                return self._deparse_coalesce(node)
            case 'ParamRef':
                return self._deparse_param_ref(node)
            case 'A_Star':
                return '*'
            case 'A_Indirection':
                return self._deparse_a_indirection(node)
            case 'A_ArrayExpr':
                return self._deparse_a_array_expr(node)
            case 'RangeVar':
                return self._deparse_range_var(node)
            case 'ResTarget':
                return self._deparse_res_target(node)
            case 'SortBy':
                return self._deparse_sort_by(node)
            case 'String':
                return node.get('sval', '')
            case 'Integer':
                return str(node.get('ival', 0))
            case 'Float':
                return node.get('fval', '0')
            case 'Boolean':
                return 'TRUE' if node.get('boolval') else 'FALSE'
            case 'Null':
                return 'NULL'
            case 'List':
                items = node.get('items', [])
                return ', '.join(self.deparse(i) for i in items)
            case 'SelectStmt':
                return self.format_select(node)
            case 'JoinExpr':
                return self._deparse_join_inline(node)
            case 'RangeSubselect':
                return self._deparse_range_subselect(node)
            case 'BooleanTest':
                return self._deparse_boolean_test(node)
            case 'SetToDefault':
                return 'DEFAULT'
            case _:
                raise ValueError(f'Unsupported node type: {node_type}')

    def _deparse_column_ref(self, node: dict) -> str:
        return '.'.join(self._extract_names(node.get('fields', [])))

    def _deparse_a_const(self, node: dict) -> str:
        if node.get('isnull'):
            return 'NULL'
        if 'ival' in node:
            return str(node['ival']['ival'])
        if 'fval' in node:
            return node['fval']['fval']
        if 'sval' in node:
            val = node['sval']['sval']
            escaped = val.replace("'", "''")
            return f"'{escaped}'"
        if 'boolval' in node:
            return 'TRUE' if node['boolval']['boolval'] else 'FALSE'
        return 'NULL'

    def _deparse_a_expr(self, node: dict) -> str:
        kind = node.get('kind', 'AEXPR_OP')
        op = self._get_operator(node.get('name', []))
        left = self.deparse(node.get('lexpr'))
        right = node.get('rexpr')

        match kind:
            case 'AEXPR_OP':
                return f'{left} {op} {self.deparse(right)}'
            case 'AEXPR_IN':
                in_kw = 'IN' if op == '=' else 'NOT IN'
                values = self._deparse_list_items(right)
                return f'{left} {in_kw} ({values})'
            case 'AEXPR_LIKE':
                return f'{left} LIKE {self.deparse(right)}'
            case 'AEXPR_ILIKE':
                return f'{left} ILIKE {self.deparse(right)}'
            case 'AEXPR_SIMILAR':
                return f'{left} SIMILAR TO {self.deparse(right)}'
            case 'AEXPR_BETWEEN' | 'AEXPR_NOT_BETWEEN':
                items = right['List']['items']
                lo = self.deparse(items[0])
                hi = self.deparse(items[1])
                between = kind == 'AEXPR_NOT_BETWEEN'
                kw = 'NOT BETWEEN' if between else 'BETWEEN'
                return f'{left} {kw} {lo} AND {hi}'
            case 'AEXPR_OP_ANY':
                return f'{left} {op} ANY ({self.deparse(right)})'
            case 'AEXPR_OP_ALL':
                return f'{left} {op} ALL ({self.deparse(right)})'
            case _:
                return f'{left} {op} {self.deparse(right)}'

    def _deparse_bool_expr(self, node: dict) -> str:
        boolop = node['boolop']
        args = node['args']
        if boolop == 'NOT_EXPR':
            inner = self.deparse(args[0])
            return self._indent_continuation('NOT (', inner, ')')
        op = ' AND ' if boolop == 'AND_EXPR' else ' OR '
        parts = []
        for arg in args:
            part = self.deparse(arg)
            if isinstance(arg, dict):
                inner_key = next(iter(arg))
                if inner_key == 'BoolExpr':
                    inner_op = arg['BoolExpr']['boolop']
                    if inner_op != boolop and inner_op != 'NOT_EXPR':
                        part = f'({part})'
            parts.append(part)
        return op.join(parts)

    def _deparse_func_call(self, node: dict) -> str:
        func_name = '.'.join(
            self._extract_names(node.get('funcname', []))
        ).upper()
        if node.get('agg_star'):
            args_str = '*'
        else:
            args = [self.deparse(a) for a in node.get('args', [])]
            distinct = 'DISTINCT ' if node.get('agg_distinct') else ''
            args_str = f'{distinct}{", ".join(args)}'
        result = f'{func_name}({args_str})'
        if 'over' in node:
            result += f' OVER ({self._deparse_window(node["over"])})'
        return result

    def _deparse_window(self, node: dict) -> str:
        parts = []
        if 'partitionClause' in node:
            exprs = ', '.join(self.deparse(e) for e in node['partitionClause'])
            parts.append(f'PARTITION BY {exprs}')
        if 'orderClause' in node:
            exprs = ', '.join(self.deparse(e) for e in node['orderClause'])
            parts.append(f'ORDER BY {exprs}')
        return ' '.join(parts)

    def _deparse_type_cast(self, node: dict) -> str:
        arg = self.deparse(node['arg'])
        type_name = self._deparse_type_name(node['typeName'])
        return f'{arg}::{type_name}'

    def _deparse_type_name(self, node: dict) -> str:
        name_parts = self._extract_names(node.get('names', []))
        # pg_catalog prefix maps to SQL-standard type names
        if len(name_parts) == 2 and name_parts[0] == 'pg_catalog':
            name = PG_TYPE_MAP.get(name_parts[1], name_parts[1].upper())
        else:
            name = '.'.join(name_parts)
        typmods = node.get('typmods', [])
        if typmods:
            mods = ', '.join(self.deparse(m) for m in typmods)
            name = f'{name}({mods})'
        if node.get('arrayBounds'):
            name += '[]'
        return name

    def _deparse_null_test(self, node: dict) -> str:
        arg = self.deparse(node['arg'])
        if node['nulltesttype'] == 'IS_NULL':
            return f'{arg} IS NULL'
        return f'{arg} IS NOT NULL'

    def _deparse_boolean_test(self, node: dict) -> str:
        arg = self.deparse(node['arg'])
        suffix = _BOOL_TEST_SQL.get(node.get('booltesttype', ''))
        return f'{arg} {suffix}' if suffix else arg

    def _deparse_sub_link(self, node: dict) -> str:
        sub_type = node.get('subLinkType', '')
        subselect = node['subselect']
        inner = self.format_select(subselect.get('SelectStmt', subselect))
        match sub_type:
            case 'EXISTS_SUBLINK':
                return f'EXISTS ({inner})'
            case 'ANY_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                return f'{test} IN ({inner})'
            case 'ALL_SUBLINK':
                test = self.deparse(node.get('testexpr'))
                op = self._get_operator(node.get('operName', []))
                return f'{test} {op} ALL ({inner})'
            case 'EXPR_SUBLINK':
                return f'({inner})'
            case _:
                return f'({inner})'

    def _deparse_case_expr(self, node: dict) -> str:
        parts = ['CASE']
        if 'arg' in node:
            parts.append(self.deparse(node['arg']))
        for when in node.get('args', []):
            parts.append(self.deparse(when))
        if 'defresult' in node:
            parts.append(f'ELSE {self.deparse(node["defresult"])}')
        parts.append('END')
        return ' '.join(parts)

    def _deparse_case_when(self, node: dict) -> str:
        expr = self.deparse(node['expr'])
        result = self.deparse(node['result'])
        return f'WHEN {expr} THEN {result}'

    def _deparse_coalesce(self, node: dict) -> str:
        args = ', '.join(self.deparse(a) for a in node.get('args', []))
        return f'COALESCE({args})'

    def _deparse_param_ref(self, node: dict) -> str:
        number = node.get('number', 0)
        return f'${number}'

    def _deparse_a_indirection(self, node: dict) -> str:
        arg = self.deparse(node['arg'])
        for idx in node.get('indirection', []):
            if 'A_Indices' in idx:
                indices = idx['A_Indices']
                if 'uidx' in indices:
                    arg += f'[{self.deparse(indices["uidx"])}]'
            elif 'String' in idx:
                arg += f'.{idx["String"]["sval"]}'
        return arg

    def _deparse_a_array_expr(self, node: dict) -> str:
        elements = ', '.join(self.deparse(e) for e in node.get('elements', []))
        return f'ARRAY[{elements}]'

    def _deparse_range_var(
        self,
        node: dict,
        *,
        include_alias: bool = True,
    ) -> str:
        parts = []
        if 'schemaname' in node:
            parts.append(node['schemaname'])
        parts.append(node['relname'])
        result = '.'.join(parts)
        if include_alias:
            alias = node.get('alias')
            if alias:
                result += f' AS {alias["aliasname"]}'
        return result

    def _deparse_range_subselect(self, node: dict) -> str:
        subquery = node['subquery']
        inner = self._format_statement(subquery)
        alias = node.get('alias')
        result = f'({inner})'
        if alias:
            result += f' AS {alias["aliasname"]}'
        return result

    def _deparse_res_target(self, node: dict) -> str:
        val = self.deparse(node.get('val'))
        name = node.get('name')
        if name:
            if '\n' in val:
                lines = val.split('\n')
                lines[-1] += f' AS {name}'
                return '\n'.join(lines)
            return f'{val} AS {name}'
        return val

    def _deparse_sort_by(self, node: dict) -> str:
        expr = self.deparse(node['node'])
        direction = node.get('sortby_dir', 'SORTBY_DEFAULT')
        nulls = node.get('sortby_nulls', 'SORTBY_NULLS_DEFAULT')
        if direction == 'SORTBY_DESC':
            expr += ' DESC'
        elif direction == 'SORTBY_ASC':
            expr += ' ASC'
        if nulls == 'SORTBY_NULLS_FIRST':
            expr += ' NULLS FIRST'
        elif nulls == 'SORTBY_NULLS_LAST':
            expr += ' NULLS LAST'
        return expr

    def _deparse_join_inline(self, node: dict) -> str:
        left = self.deparse(node['larg'])
        right = self.deparse(node['rarg'])
        kw = self._join_keyword(node)
        result = f'{left} {kw} {right}'
        quals = node.get('quals')
        if quals:
            result += f' ON {self.deparse(quals)}'
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _indent_continuation(
        prefix: str,
        content: str,
        suffix: str = '',
    ) -> str:
        """Indent continuation lines of multi-line content.

        The first line is prefixed with ``prefix``. Subsequent lines
        are padded to align with the character after the prefix.
        ``suffix`` is appended to the last line.
        """
        if '\n' not in content:
            return f'{prefix}{content}{suffix}'
        lines = content.split('\n')
        pad = ' ' * len(prefix)
        result = [f'{prefix}{lines[0]}']
        for line in lines[1:]:
            result.append(f'{pad}{line}')
        result[-1] += suffix
        return '\n'.join(result)

    @staticmethod
    def _extract_names(nodes: list[dict]) -> list[str]:
        """Extract string values from a list of AST name nodes."""
        parts = []
        for n in nodes:
            if isinstance(n, dict):
                if 'String' in n:
                    parts.append(n['String']['sval'])
                elif 'A_Star' in n:
                    parts.append('*')
                else:
                    parts.append(str(n))
            else:
                parts.append(str(n))
        return parts

    def _get_operator(self, name_nodes: list) -> str:
        if not name_nodes:
            return '='
        return '.'.join(self._extract_names(name_nodes))

    def _deparse_list_items(self, node: dict | None) -> str:
        if node is None:
            return ''
        if isinstance(node, dict) and 'List' in node:
            items = node['List'].get('items', [])
            return ', '.join(self.deparse(i) for i in items)
        return self.deparse(node)

    @staticmethod
    def _join_keyword(node: dict) -> str:
        join_type = node.get('jointype', 'JOIN_INNER')
        is_natural = node.get('isNatural', False)
        prefix = 'NATURAL ' if is_natural else ''
        match join_type:
            case 'JOIN_INNER':
                if node.get('quals') is None and not is_natural:
                    return f'{prefix}CROSS JOIN'
                return f'{prefix}INNER JOIN'
            case 'JOIN_LEFT':
                return f'{prefix}LEFT JOIN'
            case 'JOIN_RIGHT':
                return f'{prefix}RIGHT JOIN'
            case 'JOIN_FULL':
                return f'{prefix}FULL JOIN'
            case _:
                return f'{prefix}JOIN'

    @staticmethod
    def _flatten_bool_expr(
        node: dict,
        target_op: str,
    ) -> list[dict]:
        """Flatten a BoolExpr into a list of args for the same op."""
        if 'BoolExpr' not in node:
            return [node]
        bool_expr = node['BoolExpr']
        if bool_expr['boolop'] != target_op:
            return [node]
        result = []
        for arg in bool_expr['args']:
            if (
                isinstance(arg, dict)
                and 'BoolExpr' in arg
                and arg['BoolExpr']['boolop'] == target_op
            ):
                result.extend(Formatter._flatten_bool_expr(arg, target_op))
            else:
                result.append(arg)
        return result
