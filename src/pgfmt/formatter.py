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
        self._source_sql = sql
        statements = pgparse.parse(sql)
        results = []
        for stmt_wrapper in statements:
            stmt = stmt_wrapper['stmt']
            formatted = self._format_statement(
                stmt,
                stmt_wrapper,
            )
            results.append(formatted + ';')
        return '\n\n'.join(results)

    def _format_statement(
        self,
        stmt: dict,
        wrapper: dict | None = None,
    ) -> str:
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
            case 'ViewStmt':
                return self.format_view(node)
            case 'CreateStmt':
                return self.format_create_table(node)
            case 'CreateTableAsStmt':
                return self.format_create_table_as(node)
            case 'CreateFunctionStmt':
                return self.format_create_function(node)
            case 'CreateDomainStmt':
                return self._format_create_domain(node)
            case 'CreateUserMappingStmt':
                return self._format_create_user_mapping(node)
            case _:
                return self._passthrough(wrapper)

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

    @abc.abstractmethod
    def format_view(self, node: dict) -> str:
        """Format a CREATE VIEW statement."""

    @abc.abstractmethod
    def format_create_table(self, node: dict) -> str:
        """Format a CREATE TABLE statement."""

    def format_create_table_as(self, node: dict) -> str:
        """Format CREATE TABLE AS or CREATE MATERIALIZED VIEW AS."""
        objtype = node.get('objtype', '')
        into = node['into']
        rel = into['rel']
        name = self._deparse_range_var(rel, include_alias=False)
        query = node['query']
        inner = self._format_statement(query)

        if objtype == 'OBJECT_MATVIEW':
            header = f'CREATE MATERIALIZED VIEW {name} AS'
        else:
            header = f'CREATE TABLE {name} AS'

        suffix = ''
        if into.get('skipData'):
            suffix = '\nWITH NO DATA'

        return f'{header}\n{inner}{suffix}'

    def format_create_function(self, node: dict) -> str:
        """Format CREATE FUNCTION / CREATE PROCEDURE."""
        func_name = '.'.join(self._extract_names(node.get('funcname', [])))
        params = node.get('parameters', []) or []
        param_strs = []
        for p in params:
            fp = p.get('FunctionParameter', p)
            parts = []
            mode = fp.get('mode')
            if mode == 'FUNC_PARAM_OUT':
                parts.append('OUT')
            elif mode == 'FUNC_PARAM_INOUT':
                parts.append('INOUT')
            elif mode == 'FUNC_PARAM_VARIADIC':
                parts.append('VARIADIC')
            pname = fp.get('name')
            if pname:
                parts.append(pname)
            if 'argType' in fp:
                parts.append(self._deparse_type_name(fp['argType']))
            if 'defexpr' in fp:
                parts.append(f'DEFAULT {self.deparse(fp["defexpr"])}')
            param_strs.append(' '.join(parts))

        ret_type = node.get('returnType')
        returns = ''
        if ret_type:
            returns = f' RETURNS {self._deparse_type_name(ret_type)}'

        lines = [
            f'CREATE FUNCTION {func_name}({", ".join(param_strs)}){returns}'
        ]

        options = node.get('options', [])
        body = None
        for opt in options:
            elem = opt['DefElem']
            match elem['defname']:
                case 'language':
                    lang = elem['arg']['String']['sval']
                    lines.append(f'    LANGUAGE {lang}')
                case 'as':
                    items = elem['arg']['List']['items']
                    body = items[0]['String']['sval']
                case 'volatility':
                    lines.append(
                        f'    {elem["arg"]["String"]["sval"].upper()}'
                    )
                case 'security':
                    val = elem['arg']['Integer']['ival']
                    sec = (
                        'SECURITY DEFINER' if val == 1 else 'SECURITY INVOKER'
                    )
                    lines.append(f'    {sec}')
                case 'strict':
                    val = elem['arg']['Integer']['ival']
                    if val == 1:
                        lines.append('    STRICT')
                case 'set':
                    ve = elem['arg']['VariableSetStmt']
                    vname = ve.get('name', '')
                    vargs = ', '.join(
                        self.deparse(a) for a in ve.get('args', [])
                    )
                    lines.append(f'    SET {vname} TO {vargs}')

        if body is not None:
            lines.append('    AS $$')
            lines.append(body.rstrip())
            lines.append('$$')

        return '\n'.join(lines)

    def _passthrough(self, wrapper: dict | None) -> str:
        """Return the original SQL normalized to a single line."""
        source = getattr(self, '_source_sql', '')
        if not wrapper or not source:
            text = source
        else:
            loc = wrapper.get('stmt_location', 0)
            length = wrapper.get('stmt_len', 0)
            if length > 0:
                text = source[loc : loc + length]
            else:
                text = source[loc:]
        return ' '.join(text.split()).rstrip(';')

    def _format_create_domain(self, node: dict) -> str:
        name = '.'.join(self._extract_names(node.get('domainname', [])))
        base_type = self._deparse_type_name(node['typeName'])
        lines = [f'CREATE DOMAIN {name} AS {base_type}']
        for cons in node.get('constraints', []):
            c = cons['Constraint']
            lines.append(f'    {self._deparse_column_constraint(c)}')
        return '\n'.join(lines)

    def _format_create_user_mapping(self, node: dict) -> str:
        user = node['user']
        rolename = user.get('rolename', 'PUBLIC')
        server = node['servername']
        lines = [
            f'CREATE USER MAPPING FOR {rolename} SERVER {server}',
        ]
        options = node.get('options', [])
        if options:
            opt_parts = []
            for opt in options:
                elem = opt['DefElem']
                name = elem['defname']
                arg = elem.get('arg')
                if arg and 'String' in arg:
                    val = arg['String']['sval']
                    opt_parts.append(f"    {name} '{val}'")
                else:
                    opt_parts.append(f'    {name}')
            lines.append('OPTIONS (')
            lines.append(',\n'.join(opt_parts))
            lines.append(')')
        return '\n'.join(lines)

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
            case 'RangeFunction':
                return self._deparse_range_function(node)
            case 'SQLValueFunction':
                return self._deparse_sql_value_function(node)
            case 'ColumnDef':
                return self._deparse_column_def(node)
            case 'Constraint':
                return self._deparse_constraint(node)
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
            return 'TRUE' if node['boolval'].get('boolval') else 'FALSE'
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
        if len(name_parts) == 2 and name_parts[0] == 'pg_catalog':
            name = PG_TYPE_MAP.get(
                name_parts[1],
                name_parts[1].upper(),
            )
        elif len(name_parts) == 1:
            name = PG_TYPE_MAP.get(
                name_parts[0],
                name_parts[0].upper(),
            )
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

    def _deparse_column_def(self, node: dict) -> str:
        name = node['colname']
        type_name = self._deparse_type_name(node['typeName'])
        parts = [name, type_name]
        for cons in node.get('constraints', []):
            c = cons['Constraint']
            parts.append(self._deparse_column_constraint(c))
        return ' '.join(parts)

    def _deparse_column_constraint(self, node: dict) -> str:
        contype = node.get('contype', '')
        match contype:
            case 'CONSTR_NOTNULL':
                return 'NOT NULL'
            case 'CONSTR_NULL':
                return 'NULL'
            case 'CONSTR_DEFAULT':
                expr = self.deparse(node.get('raw_expr'))
                return f'DEFAULT {expr}'
            case 'CONSTR_PRIMARY':
                return 'PRIMARY KEY'
            case 'CONSTR_UNIQUE':
                return 'UNIQUE'
            case 'CONSTR_CHECK':
                expr = self.deparse(node.get('raw_expr'))
                conname = node.get('conname')
                if conname:
                    return f'CONSTRAINT {conname} CHECK ({expr})'
                return f'CHECK ({expr})'
            case 'CONSTR_FOREIGN':
                return self._deparse_fk_constraint(node)
            case _:
                return ''

    def _deparse_constraint(self, node: dict) -> str:
        """Deparse a table-level constraint."""
        contype = node.get('contype', '')
        conname = node.get('conname')
        prefix = f'CONSTRAINT {conname} ' if conname else ''
        match contype:
            case 'CONSTR_PRIMARY':
                keys = self._extract_names(node.get('keys', []))
                return f'{prefix}PRIMARY KEY ({", ".join(keys)})'
            case 'CONSTR_UNIQUE':
                keys = self._extract_names(node.get('keys', []))
                return f'{prefix}UNIQUE ({", ".join(keys)})'
            case 'CONSTR_CHECK':
                expr = self.deparse(node.get('raw_expr'))
                return f'{prefix}CHECK ({expr})'
            case 'CONSTR_FOREIGN':
                fk_attrs = self._extract_names(node.get('fk_attrs', []))
                result = f'{prefix}FOREIGN KEY ({", ".join(fk_attrs)})'
                result += ' ' + self._deparse_fk_constraint(node)
                return result
            case _:
                return ''

    def _deparse_fk_constraint(self, node: dict) -> str:
        pktable = node['pktable']
        pk_name = self._deparse_range_var(
            pktable,
            include_alias=False,
        )
        pk_attrs = self._extract_names(node.get('pk_attrs', []))
        result = f'REFERENCES {pk_name}'
        if pk_attrs:
            result += f' ({", ".join(pk_attrs)})'
        fk_actions = {
            'a': None,
            'r': 'RESTRICT',
            'c': 'CASCADE',
            'n': 'SET NULL',
            'd': 'SET DEFAULT',
        }
        del_action = fk_actions.get(node.get('fk_del_action', 'a'))
        upd_action = fk_actions.get(node.get('fk_upd_action', 'a'))
        if del_action:
            result += f' ON DELETE {del_action}'
        if upd_action:
            result += f' ON UPDATE {upd_action}'
        return result

    def _deparse_storage_options(
        self,
        options: list[dict],
    ) -> str:
        parts = []
        for opt in options:
            elem = opt['DefElem']
            name = elem['defname']
            ns = elem.get('defnamespace')
            if ns:
                name = f'{ns}.{name}'
            arg = elem.get('arg')
            if arg and 'String' in arg:
                val = arg['String']['sval']
                parts.append(f"{name}='{val}'")
            elif arg and 'Integer' in arg:
                val = arg['Integer']['ival']
                parts.append(f'{name}={val}')
            else:
                parts.append(name)
        return ', '.join(parts)

    @staticmethod
    def _deparse_sql_value_function(node: dict) -> str:
        op = node.get('op', '')
        return {
            'SVFOP_CURRENT_TIMESTAMP': 'CURRENT_TIMESTAMP',
            'SVFOP_CURRENT_DATE': 'CURRENT_DATE',
            'SVFOP_CURRENT_TIME': 'CURRENT_TIME',
            'SVFOP_CURRENT_USER': 'CURRENT_USER',
            'SVFOP_SESSION_USER': 'SESSION_USER',
            'SVFOP_LOCALTIME': 'LOCALTIME',
            'SVFOP_LOCALTIMESTAMP': 'LOCALTIMESTAMP',
            'SVFOP_CURRENT_ROLE': 'CURRENT_ROLE',
            'SVFOP_CURRENT_CATALOG': 'CURRENT_CATALOG',
            'SVFOP_CURRENT_SCHEMA': 'CURRENT_SCHEMA',
            'SVFOP_USER': 'USER',
        }.get(op, op.removeprefix('SVFOP_'))

    def _deparse_range_function(self, node: dict) -> str:
        functions = node.get('functions', [])
        parts = []
        for func_item in functions:
            if isinstance(func_item, dict) and 'List' in func_item:
                items = func_item['List'].get('items', [])
                if items:
                    parts.append(self.deparse(items[0]))
            else:
                parts.append(self.deparse(func_item))
        result = ', '.join(parts)
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
        using = node.get('usingClause')
        if using:
            cols = ', '.join(self._extract_names(using))
            result += f' USING ({cols})'
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_distinct(
        self,
        distinct_clause: list | None,
    ) -> str:
        """Format a DISTINCT or DISTINCT ON clause prefix."""
        if distinct_clause is None:
            return ''
        has_columns = any(
            isinstance(item, dict) and item for item in distinct_clause
        )
        if not has_columns:
            return 'DISTINCT '
        cols = ', '.join(
            self.deparse(item)
            for item in distinct_clause
            if isinstance(item, dict) and item
        )
        return f'DISTINCT ON ({cols}) '

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

    def _join_keyword(self, node: dict) -> str:
        join_type = node.get('jointype', 'JOIN_INNER')
        is_natural = node.get('isNatural', False)
        prefix = 'NATURAL ' if is_natural else ''
        match join_type:
            case 'JOIN_INNER':
                has_condition = (
                    node.get('quals') is not None
                    or node.get('usingClause') is not None
                )
                if not has_condition and not is_natural:
                    return f'{prefix}CROSS JOIN'
                if self._is_plain_join(node):
                    return f'{prefix}JOIN'
                return f'{prefix}INNER JOIN'
            case 'JOIN_LEFT':
                return f'{prefix}LEFT JOIN'
            case 'JOIN_RIGHT':
                return f'{prefix}RIGHT JOIN'
            case 'JOIN_FULL':
                return f'{prefix}FULL JOIN'
            case _:
                return f'{prefix}JOIN'

    def _is_plain_join(self, node: dict) -> bool:
        """Check the source SQL to see if JOIN was written without INNER."""
        source = getattr(self, '_source_sql', None)
        if not source:
            return False
        larg_loc = self._rightmost_location(node.get('larg', {}))
        rarg_loc = self._leftmost_location(node.get('rarg', {}))
        if larg_loc < 0 or rarg_loc < 0:
            return False
        between = source[larg_loc:rarg_loc].upper()
        return ' JOIN ' in between and ' INNER ' not in between

    @staticmethod
    def _leftmost_location(node: dict) -> int:
        if not isinstance(node, dict):
            return -1
        for value in node.values():
            if isinstance(value, dict) and 'location' in value:
                return value['location']
        return -1

    @staticmethod
    def _rightmost_location(node: dict) -> int:
        if not isinstance(node, dict):
            return -1
        for value in node.values():
            if isinstance(value, dict):
                loc = value.get('location', -1)
                name = value.get('relname', '')
                if loc >= 0:
                    return loc + len(name)
        return -1

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
