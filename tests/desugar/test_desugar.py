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


# ---------------------------------------------------------------------------
# B-020: proc-blocos — expansão, ciclos, aninhamento
# ---------------------------------------------------------------------------

_PB_BASE = '''\
program "T"
vars {{ s: Number {extra_vars}}}
procs {{
    Proc(msg: Text) from "Lib.macro" {{
        codes SUCESSO<0>, ERRO<1>
    }}
    {proc_block}
}}
exec Proc(msg="x") >> s {{
    pass SUCESSO, ERRO
}}
'''


def _pb_src(proc_block: str, extra_vars: str = '') -> str:
    return _PB_BASE.format(proc_block=proc_block, extra_vars=extra_vars)


class TestProcBlockDesugar:
    """Testes de expansão de proc-blocos no desugar — B-020."""

    # --- T1: expansão simples (terminal) ---

    def test_proc_block_removed_from_procedures(self):
        """Proc-bloco não deve aparecer em procedures após desugar."""
        src = _pb_src(
            'Bloco(msg: Text) {\n'
            '    exec Proc(msg=msg) as "B" {\n'
            '        pass SUCESSO, ERRO\n'
            '    }\n'
            '}'
        )
        ast = desugar(parse(src))
        names = {p.name for p in ast.procedures}
        assert 'Bloco' not in names
        assert 'Proc' in names

    def test_proc_block_inline_call_expands(self):
        """@Bloco() no corpo de um case deve ser expandido para ExecBlockNode."""
        src = '''\
program "T"
vars { s: Number }
procs {
    Proc(msg: Text) from "Lib.macro" {
        codes SUCESSO<0>, ERRO<1>
    }
    Bloco(msg: Text) {
        exec Proc(msg=msg) as "B" {
            pass SUCESSO, ERRO
        }
    }
}
exec Proc(msg="x") >> s {
    case SUCESSO: @Bloco(msg="ok")
    pass ERRO
}
'''
        ast = desugar(parse(src))
        case_block = ast.block.cases[0].block
        assert isinstance(case_block, ExecBlockNode)
        assert case_block.proc_name == 'Proc'

    def test_proc_block_lit_param_substituted(self):
        """Placeholder lit (msg: Text) deve ser substituído pelo valor literal da chamada."""
        src = '''\
program "T"
vars { s: Number }
procs {
    Proc(msg: Text) from "Lib.macro" {
        codes SUCESSO<0>, ERRO<1>
    }
    Bloco(msg: Text) {
        exec Proc(msg=msg) as "B" {
            pass SUCESSO, ERRO
        }
    }
}
exec Proc(msg="x") >> s {
    case SUCESSO: @Bloco(msg="hello")
    pass ERRO
}
'''
        ast = desugar(parse(src))
        case_block = ast.block.cases[0].block
        from compiler.parser import ArgNode
        assert case_block.kwargs['msg'] == ArgNode(value='hello', evaluation='literal')

    def test_proc_block_ref_param_substituted(self):
        """Placeholder ref (&home) deve ser substituído pela variável real da chamada."""
        src = '''\
program "T"
vars { s: Number
       home_var: Text }
procs {
    Proc(msg: Text) from "Lib.macro" {
        codes SUCESSO<0>, ERRO<1>
    }
    Bloco(home: &Text) {
        exec Proc(msg=&home) as "B" {
            pass SUCESSO, ERRO
        }
    }
}
exec Proc(msg="x") >> s {
    case SUCESSO: @Bloco(home=&home_var)
    pass ERRO
}
'''
        ast = desugar(parse(src))
        case_block = ast.block.cases[0].block
        from compiler.parser import ArgNode
        assert case_block.kwargs['msg'] == ArgNode(value='home_var', evaluation='reference')

    # --- T2: ciclo → DesugarError ---

    def test_direct_cycle_raises(self):
        """Proc-bloco que se referencia diretamente deve levantar DesugarError."""
        src = '''\
program "T"
vars { s: Number }
procs {
    Proc() from "Lib.macro" {
        codes SUCESSO<0>, ERRO<1>
    }
    A() {
        exec Proc() as "root" {
            case SUCESSO: @A()
            pass ERRO
        }
    }
}
exec Proc() >> s {
    pass SUCESSO, ERRO
}
'''
        from compiler.desugar import DesugarError
        with pytest.raises(DesugarError, match="recursão"):
            desugar(parse(src))

    def test_indirect_cycle_raises(self):
        """Ciclo indireto A → B → A deve levantar DesugarError."""
        src = '''\
program "T"
vars { s: Number }
procs {
    Proc() from "Lib.macro" {
        codes SUCESSO<0>, ERRO<1>
    }
    A() {
        exec Proc() as "root" {
            case SUCESSO: @B()
            pass ERRO
        }
    }
    B() {
        exec Proc() as "root" {
            case SUCESSO: @A()
            pass ERRO
        }
    }
}
exec Proc() >> s {
    pass SUCESSO, ERRO
}
'''
        from compiler.desugar import DesugarError
        with pytest.raises(DesugarError, match="recursão"):
            desugar(parse(src))

    # --- T3: expansão aninhada (proc-bloco usa outro proc-bloco) ---

    def test_nested_proc_block_expansion(self):
        """Proc-bloco B que usa proc-bloco A deve ser expandido corretamente."""
        src = '''\
program "T"
vars { s: Number }
procs {
    Proc(msg: Text) from "Lib.macro" {
        codes SUCESSO<0>, ERRO<1>
    }
    A(msg: Text) {
        exec Proc(msg=msg) as "A-inner" {
            pass SUCESSO, ERRO
        }
    }
    B(msg: Text) {
        exec Proc(msg="outer") as "B-outer" {
            case SUCESSO: @A(msg=msg)
            pass ERRO
        }
    }
}
exec Proc(msg="x") >> s {
    case SUCESSO: @B(msg="hello")
    pass ERRO
}
'''
        ast = desugar(parse(src))
        case_b = ast.block.cases[0].block
        # B expandido: exec Proc(msg="outer") { case SUCESSO: A expandido }
        assert case_b.proc_name == 'Proc'
        assert case_b.kwargs['msg'].value == 'outer'
        # Dentro do case SUCESSO de B: A expandido = exec Proc(msg="hello")
        case_a = case_b.cases[0].block
        assert case_a.proc_name == 'Proc'
        assert case_a.kwargs['msg'].value == 'hello'


# ---------------------------------------------------------------------------
# B-024: while inline — múltiplos códigos e códigos borbulhados
# ---------------------------------------------------------------------------

_B024_BASE = '''\
program "T"
vars {{ s: Number }}
procs {{
    f() from "A.b" {{
        codes OK<0>, ERR<1>
    }}
}}
{body}
'''


def _b024_src(body: str) -> str:
    return _B024_BASE.format(body=body)


class TestWhileMultipleCodes:
    """Testes de while inline com múltiplos códigos e borbulhamento — B-024."""

    def test_while_two_codes_loop_while(self):
        """while(ERR, OK) no átomo terminal → loop_while = ['ERR', 'OK']."""
        src = _b024_src('@f() while(ERR, OK)')
        ast = desugar(parse(src))
        assert set(ast.block.loop_while) == {'ERR', 'OK'}

    def test_while_two_codes_pass_codes_empty(self):
        """Com while(ERR, OK) cobrindo todos os códigos → pass_codes vazio."""
        src = _b024_src('@f() while(ERR, OK)')
        ast = desugar(parse(src))
        assert ast.block.pass_codes == []

    def test_while_bubbled_code_no_error(self):
        """Código não declarado no proc (borbulhado) não deve levantar erro no desugar."""
        src = _b024_src('@f() while(BUBBLED) when(OK)\n@f() >> s')
        ast = desugar(parse(src))
        assert 'BUBBLED' in ast.block.loop_while

    def test_while_two_codes_chained_pass_set(self):
        """while(ERR, BUBBLED) when(OK): pass deve excluir ERR, BUBBLED e OK."""
        src = _b024_src('@f() while(ERR, BUBBLED) when(OK)\n@f() >> s')
        ast = desugar(parse(src))
        # all codes de f() = {OK, ERR}; while_set = {ERR, BUBBLED}; when = OK
        # pass = {OK, ERR} - {OK} - {ERR, BUBBLED} = {} (BUBBLED não estava em all_codes)
        assert 'OK' not in ast.block.pass_codes
        assert 'ERR' not in ast.block.pass_codes

