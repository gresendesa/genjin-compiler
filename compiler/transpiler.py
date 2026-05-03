"""
Etapa 3:
Transpilação/geração da AST para a notação Genjin
Saída: notação Genjin pronta para o assemblador
"""

from __future__ import annotations

from compiler.parser import (
    ProgramNode, VarDeclNode, ProcDeclNode, ParamDeclNode,
    OutputCodeNode, ExecBlockNode, CaseNode, ArgNode,
    parse,
)


# ---------------------------------------------------------------------------
# Writer com indentação
# ---------------------------------------------------------------------------

class _Writer:
    """Acumula linhas com controle de indentação."""

    _INDENT = '    '

    def __init__(self):
        self._lines: list[str] = []
        self._depth = 0

    def line(self, text: str = '') -> None:
        if text:
            self._lines.append(self._INDENT * self._depth + text)
        else:
            self._lines.append('')

    def indent(self) -> None:
        self._depth += 1

    def dedent(self) -> None:
        self._depth -= 1

    def result(self) -> str:
        return '\n'.join(self._lines) + '\n'


# ---------------------------------------------------------------------------
# Helpers de formatação Jinja2
# ---------------------------------------------------------------------------

def _jstr(value: str) -> str:
    """String Jinja2 com aspas simples."""
    escaped = value.replace('\\', '\\\\').replace("'", "\\'")
    return f"'{escaped}'"


def _jval(value) -> str:
    """Literal Jinja2 para str, int ou None."""
    if value is None:
        return 'none'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _jstr(value)
    raise TypeError(f"Tipo não suportado: {type(value)}")


def _jlist(items: list[str]) -> str:
    """Lista Jinja2 compacta de strings já formatadas."""
    if not items:
        return '[]'
    inner = ', '.join(items)
    return f'[{inner}]'


# ---------------------------------------------------------------------------
# Transpiler
# ---------------------------------------------------------------------------

class Transpiler:
    """Gera um template Jinja2 a partir do AST de um programa .gnj."""

    def __init__(self, ast: ProgramNode):
        self._ast = ast

    def transpile(self) -> str:
        w = _Writer()
        w.line('{* from "genjin" import ATTRIBUTE, TYPE, CARDINALITY, EVALUATION, MACROMOD, build *}')
        w.line()
        w.line('{*')
        w.indent()
        w.line('set program = {')
        w.indent()
        self._write_program_fields(w, self._ast)
        w.dedent()
        w.line('}')
        w.dedent()
        w.line('*}')
        w.line()
        w.line('{{ build(prog=program, language_renderer=MACROMOD) }}')
        return w.result()

    # ------------------------------------------------------------------
    # Program
    # ------------------------------------------------------------------

    def _write_program_fields(self, w: _Writer, ast: ProgramNode) -> None:
        w.line(f'ATTRIBUTE.NAME: {_jstr(ast.name)},')
        w.line('ATTRIBUTE.VARIABLES: [')
        w.indent()
        for var in ast.variables:
            self._write_var(w, var)
        w.dedent()
        w.line('],')
        w.line('ATTRIBUTE.PROCEDURES: [')
        w.indent()
        for proc in ast.procedures:
            self._write_proc(w, proc)
        w.dedent()
        w.line('],')
        w.line('ATTRIBUTE.BLOCK:')
        self._write_block(w, ast.block)

    # ------------------------------------------------------------------
    # Variable
    # ------------------------------------------------------------------

    def _write_var(self, w: _Writer, var: VarDeclNode) -> None:
        type_expr = f'TYPE.{var.type.upper()}'
        card_expr = f'CARDINALITY.{var.cardinality.upper()}'
        w.line('{')
        w.indent()
        w.line(f'ATTRIBUTE.NAME: {_jstr(var.name)},')
        w.line(f'ATTRIBUTE.TYPE: {type_expr},')
        if var.value is not None:
            w.line(f'ATTRIBUTE.CARDINALITY: {card_expr},')
            w.line(f'ATTRIBUTE.VALUE: {_jval(var.value)}')
        else:
            w.line(f'ATTRIBUTE.CARDINALITY: {card_expr}')
        w.dedent()
        w.line('},')

    # ------------------------------------------------------------------
    # Procedure
    # ------------------------------------------------------------------

    def _write_proc(self, w: _Writer, proc: ProcDeclNode) -> None:
        macro_expr = f"[{_jstr(proc.library)}, {_jstr(proc.macro)}]"
        w.line('{')
        w.indent()
        w.line(f'ATTRIBUTE.NAME: {_jstr(proc.name)},')
        w.line(f'ATTRIBUTE.MACRO: {macro_expr},')
        w.line('ATTRIBUTE.PARAMETERS: [')
        w.indent()
        for param in proc.parameters:
            self._write_param(w, param)
        w.dedent()
        w.line('],')
        w.line('ATTRIBUTE.OUTPUT_CODES: [')
        w.indent()
        for code in proc.output_codes:
            self._write_output_code(w, code)
        w.dedent()
        w.line(']')
        w.dedent()
        w.line('},')

    def _write_param(self, w: _Writer, param: ParamDeclNode) -> None:
        type_expr = f'TYPE.{param.type.upper()}'
        card_expr = f'CARDINALITY.{param.cardinality.upper()}'
        eval_expr = f'EVALUATION.{param.evaluation.upper()}'
        w.line('{')
        w.indent()
        w.line(f'ATTRIBUTE.NAME: {_jstr(param.name)},')
        w.line(f'ATTRIBUTE.TYPE: {type_expr},')
        w.line(f'ATTRIBUTE.CARDINALITY: {card_expr},')
        w.line(f'ATTRIBUTE.EVALUATION: {eval_expr}')
        w.dedent()
        w.line('},')

    def _write_output_code(self, w: _Writer, code: OutputCodeNode) -> None:
        w.line(f'{{ATTRIBUTE.NAME: {_jstr(code.name)}, ATTRIBUTE.CODE: {code.code}}},')

    # ------------------------------------------------------------------
    # Exec block
    # ------------------------------------------------------------------

    def _write_block(self, w: _Writer, block: ExecBlockNode) -> None:
        block_name = block.block_name if block.block_name is not None else block.proc_name
        w.line('{')
        w.indent()
        # ATTRIBUTE.VARIABLE só emitido se >> foi explicitamente declarado
        if block.variable_explicit and block.variable is not None:
            w.line(f'ATTRIBUTE.VARIABLE: {_jstr(block.variable)},')
        w.line(f'ATTRIBUTE.NAME: {_jstr(block_name)},')
        w.line('ATTRIBUTE.PROCEDURE: {')
        w.indent()
        w.line(f'ATTRIBUTE.NAME: {_jstr(block.proc_name)},')
        w.line('ATTRIBUTE.KEYWORD_ARGS: {')
        w.indent()
        for kwarg_name, arg in block.kwargs.items():
            eval_expr = f'EVALUATION.{arg.evaluation.upper()}'
            val_expr = arg.value if arg.raw else _jval(arg.value)
            w.line(f'{_jstr(kwarg_name)}: {{ATTRIBUTE.VALUE: {val_expr}, ATTRIBUTE.EVALUATION: {eval_expr}}},')
        w.dedent()
        w.line('}')
        w.dedent()
        w.line('},')
        w.line('ATTRIBUTE.CASES: [')
        w.indent()
        for case in block.cases:
            self._write_case(w, case)
        w.dedent()
        w.line('],')
        loop_items = _jlist([_jstr(c) for c in block.loop_while])
        w.line(f'ATTRIBUTE.LOOP_WHILE: {loop_items},')
        pass_items = _jlist([_jstr(c) for c in block.pass_codes])
        w.line(f'ATTRIBUTE.PASS_CODES: {pass_items}')
        w.dedent()
        w.line('}')

    def _write_case(self, w: _Writer, case: CaseNode) -> None:
        w.line('{')
        w.indent()
        w.line(f'ATTRIBUTE.OUTPUT_CODE: {_jstr(case.output_code)},')
        w.line('ATTRIBUTE.BLOCK:')
        self._write_block(w, case.block)
        w.dedent()
        w.line('},')


# ---------------------------------------------------------------------------
# Função de conveniência
# ---------------------------------------------------------------------------

def transpile(source: str) -> str:
    """Tokeniza, parseia e transpila um programa .gnj para Jinja2."""
    ast = parse(source)
    return Transpiler(ast).transpile()


if __name__ == '__main__':
    import argparse
    import sys
    from compiler.ast_io import ast_from_json
    from compiler.scanner import ScannerError
    from compiler.parser import ParseError

    ap = argparse.ArgumentParser(prog='python -m compiler.transpiler')
    ap.add_argument('ast_file', nargs='?', help='arquivo JSON da AST (padrão: stdin)')
    ap.add_argument('--source', metavar='ARQUIVO', help='arquivo .gnj (executa pipeline completo diretamente)')
    args = ap.parse_args()

    if args.source and args.ast_file:
        ap.error('use --source OU arquivo de AST, não os dois')

    try:
        if args.source:
            source = open(args.source, encoding='utf-8').read()
            result = transpile(source)
        else:
            raw = open(args.ast_file, encoding='utf-8').read() if args.ast_file else sys.stdin.read()
            ast = ast_from_json(raw)
            result = Transpiler(ast).transpile()
    except OSError as exc:
        print(f'Erro ao ler arquivo: {exc}', file=sys.stderr)
        sys.exit(2)
    except (ScannerError, ParseError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(result, end='')
