"""
Testes unitários do Desugar — fase 2.5 do compilador Genjin.

Cobre:
  - Tipo 1: @proc() expandido para ExecBlockNode canônico
  - Tipo 2: @proc() when(CODE) expandido com case aninhado
  - Encadeamento de múltiplos átomos
  - while em átomos inline
  - >> em átomos (herança de variável)
  - Terminal canônico exec {}
  - Recursão: inline dentro de case de exec canônico
"""

import pytest
from compiler.parser import (
    parse, ProgramNode, ExecBlockNode, CaseNode, InlineSeqNode,
)
from compiler.desugar import desugar, DesugarError


def make_desugared(source: str) -> ProgramNode:
    return desugar(parse(source))


# Fonte base reutilizável
_BASE = '''\
program "T"
vars {{ s: Number }}
procs {{ f() from "A.b" {{ codes OK<0>, ERR<1> }} }}
{exec}
'''


def _src(exec_block: str) -> str:
    return _BASE.format(exec=exec_block)


# ---------------------------------------------------------------------------
# Saída do desugar é sempre ExecBlockNode
# ---------------------------------------------------------------------------

class TestDesugarOutputType:
    def test_canonical_exec_unchanged(self):
        """Exec canônico passa pelo desugar inalterado (tipo)."""
        src = _src('exec f() >> s { pass OK, ERR }')
        ast = make_desugared(src)
        assert isinstance(ast.block, ExecBlockNode)

    def test_inline_tipo1_produces_exec_block(self):
        """@proc() ao nível raiz produz ExecBlockNode após desugar."""
        src = _src('@f() >> s')
        ast = make_desugared(src)
        assert isinstance(ast.block, ExecBlockNode)

    def test_inline_tipo2_produces_exec_block(self):
        """@proc() when(CODE) + @proc() produz ExecBlockNode após desugar."""
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        assert isinstance(ast.block, ExecBlockNode)

    def test_no_inline_seq_remaining(self):
        """Após desugar não há mais InlineSeqNode na AST."""
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)

        def _check(node):
            assert not isinstance(node, InlineSeqNode), f"InlineSeqNode não esperado: {node}"
            if isinstance(node, ExecBlockNode):
                for case in node.cases:
                    _check(case.block)

        _check(ast.block)


# ---------------------------------------------------------------------------
# Tipo 1: @proc() → ExecBlockNode simples
# ---------------------------------------------------------------------------

class TestTipo1:
    def test_proc_name(self):
        src = _src('@f() >> s')
        ast = make_desugared(src)
        assert ast.block.proc_name == 'f'

    def test_variable(self):
        src = _src('@f() >> s')
        ast = make_desugared(src)
        assert ast.block.variable == 's'
        assert ast.block.variable_explicit is True

    def test_no_cases(self):
        src = _src('@f() >> s')
        ast = make_desugared(src)
        assert ast.block.cases == []

    def test_pass_all_codes_no_while(self):
        """Sem while: pass deve conter todos os códigos do proc (OK, ERR)."""
        src = _src('@f() >> s')
        ast = make_desugared(src)
        assert set(ast.block.pass_codes) == {'OK', 'ERR'}

    def test_pass_codes_excludes_while(self):
        """Com while(ERR): pass deve conter apenas OK."""
        src = _src('@f() >> s while(ERR)')
        ast = make_desugared(src)
        assert set(ast.block.pass_codes) == {'OK'}
        assert ast.block.loop_while == ['ERR']

    def test_loop_while(self):
        src = _src('@f() >> s while(ERR)')
        ast = make_desugared(src)
        assert ast.block.loop_while == ['ERR']

    def test_no_while(self):
        src = _src('@f() >> s')
        ast = make_desugared(src)
        assert ast.block.loop_while == []

    def test_inherited_variable_none(self):
        """Sem >> na raiz: variable deve ser None (herdado do contexto None)."""
        src = _src('@f()')
        ast = make_desugared(src)
        assert ast.block.variable is None
        assert ast.block.variable_explicit is False


# ---------------------------------------------------------------------------
# Tipo 2: @proc() when(CODE) → ExecBlockNode com case aninhado
# ---------------------------------------------------------------------------

class TestTipo2:
    def test_outer_proc_name(self):
        """Átomo chained vira o bloco externo."""
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        assert ast.block.proc_name == 'f'

    def test_outer_has_one_case(self):
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        assert len(ast.block.cases) == 1
        assert ast.block.cases[0].output_code == 'OK'

    def test_outer_pass_excludes_when_code(self):
        """Outer pass = codes(proc) - {when_code} - while_set = {ERR}."""
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        assert set(ast.block.pass_codes) == {'ERR'}

    def test_inner_is_exec_block(self):
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        inner = ast.block.cases[0].block
        assert isinstance(inner, ExecBlockNode)

    def test_inner_proc_name(self):
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        inner = ast.block.cases[0].block
        assert inner.proc_name == 'f'

    def test_inner_pass_codes_from_proc(self):
        """Terminal: pass = codes(proc) - while_set = {OK, ERR} (sem while)."""
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        inner = ast.block.cases[0].block
        # Terminal sempre: codes(proc) - while_set = {OK, ERR} - {} = {OK, ERR}
        assert set(inner.pass_codes) == {'OK', 'ERR'}

    def test_inner_no_cases(self):
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        inner = ast.block.cases[0].block
        assert inner.cases == []

    def test_chained_with_while(self):
        """Átomo chained com while(ERR) when(OK):
           outer.loop_while=['ERR'], outer.pass_codes=[] (ERR em while, OK em when).
        """
        src = _src('@f() while(ERR) when(OK)\n@f() >> s')
        ast = make_desugared(src)
        assert ast.block.loop_while == ['ERR']
        assert set(ast.block.pass_codes) == set()  # codes - {OK} - {ERR} = {}

    def test_three_atoms(self):
        """@f() when(OK) + @f() when(ERR) + @f() >> s → dois níveis de aninhamento."""
        src = _src('@f() when(OK)\n@f() when(ERR)\n@f() >> s')
        ast = make_desugared(src)
        # Outer (atom1)
        assert ast.block.cases[0].output_code == 'OK'
        # Middle (atom2)
        middle = ast.block.cases[0].block
        assert middle.cases[0].output_code == 'ERR'
        # Inner terminal (atom3)
        inner = middle.cases[0].block
        assert inner.cases == []


# ---------------------------------------------------------------------------
# Herança de variável
# ---------------------------------------------------------------------------

class TestVariableInheritance:
    def test_variable_inherited_in_terminal(self):
        """Átomo chained com >> propaga var para o terminal."""
        src = _src('@f() >> s when(OK)\n@f()')
        ast = make_desugared(src)
        # outer tem variable=s; inner herda s
        inner = ast.block.cases[0].block
        assert inner.variable == 's'
        assert inner.variable_explicit is False

    def test_terminal_explicit_overrides(self):
        """Terminal com >> próprio usa a própria var."""
        src = _src('@f() when(OK)\n@f() >> s')
        ast = make_desugared(src)
        inner = ast.block.cases[0].block
        assert inner.variable == 's'
        assert inner.variable_explicit is True


# ---------------------------------------------------------------------------
# Inline dentro de case de exec canônico
# ---------------------------------------------------------------------------

class TestInlineInCase:
    _SRC = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<1> } }
exec f() >> s {
    case OK: @f()
    pass ERR
}
'''

    def test_case_body_desugared(self):
        ast = make_desugared(self._SRC)
        case_block = ast.block.cases[0].block
        assert isinstance(case_block, ExecBlockNode)

    def test_case_body_pass_codes(self):
        """Terminal no case: pass = codes(proc) - while_set = {OK, ERR}."""
        ast = make_desugared(self._SRC)
        case_block = ast.block.cases[0].block
        # Terminal sempre: codes(proc) - while_set = {OK, ERR}
        assert set(case_block.pass_codes) == {'OK', 'ERR'}


# ---------------------------------------------------------------------------
# Terminal canônico exec {}
# ---------------------------------------------------------------------------

class TestCanonicalTerminal:
    def test_canonical_terminal_preserved(self):
        """Seq com exec canônico como terminal: terminal desugared recursivamente."""
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<1> } }
exec f() >> s {
    case OK: @f() when(OK)
             exec f() { pass OK, ERR }
    pass ERR
}
'''
        ast = make_desugared(src)
        # case OK body deve ser ExecBlockNode (outer do @f() when(OK))
        outer = ast.block.cases[0].block
        assert isinstance(outer, ExecBlockNode)
        # inner do case OK do outer é o exec canônico
        inner = outer.cases[0].block
        assert isinstance(inner, ExecBlockNode)
        assert inner.pass_codes == ['ERR', 'OK'] or set(inner.pass_codes) == {'OK', 'ERR'}
