"""
Testes unitários do Parser — Etapa 2 do compilador Genjin.

Cobre:
  - Parsing correto de program, vars, procs e exec
  - Estrutura da AST (tipos e valores dos nós)
  - Herança de variável em exec aninhado
  - Resolução de `from` (split no último ponto)
  - Validações semânticas (5 regras de B-005)
  - ParseError com mensagem e linha
  - examples/basic.gnj parseado completo
"""

import pytest
from compiler.parser import (
    parse, Parser, ParseError,
    ProgramNode, VarDeclNode, ProcDeclNode, ParamDeclNode,
    OutputCodeNode, ExecBlockNode, CaseNode, ArgNode,
    InlineAtomNode, InlineSeqNode,
)
from compiler.scanner import Scanner


def make_ast(source: str) -> ProgramNode:
    return parse(source)


# ---------------------------------------------------------------------------
# Programa mínimo válido
# ---------------------------------------------------------------------------

MINIMAL = '''\
program "Minimo"
vars {
    s: Number
}
procs {
    foo() from "Lib.bar" {
        codes OK<0>
    }
}
exec foo() >> s {
    pass OK
}
'''


class TestMinimalProgram:
    def test_returns_program_node(self):
        ast = make_ast(MINIMAL)
        assert isinstance(ast, ProgramNode)

    def test_program_name(self):
        assert make_ast(MINIMAL).name == 'Minimo'

    def test_one_variable(self):
        ast = make_ast(MINIMAL)
        assert len(ast.variables) == 1

    def test_one_procedure(self):
        ast = make_ast(MINIMAL)
        assert len(ast.procedures) == 1

    def test_root_exec_proc_name(self):
        ast = make_ast(MINIMAL)
        assert ast.block.proc_name == 'foo'

    def test_root_exec_variable(self):
        ast = make_ast(MINIMAL)
        assert ast.block.variable == 's'

    def test_root_pass_codes(self):
        ast = make_ast(MINIMAL)
        assert ast.block.pass_codes == ['OK']


# ---------------------------------------------------------------------------
# Variáveis
# ---------------------------------------------------------------------------

class TestVarDecl:
    def test_singular_number(self):
        src = '''\
program "T"
vars { n: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> n { pass OK }
'''
        ast = make_ast(src)
        v = ast.variables[0]
        assert v.name == 'n'
        assert v.type == 'number'
        assert v.cardinality == 'singular'
        assert v.value is None

    def test_singular_text_with_value(self):
        src = '''\
program "T"
vars { s: Text = "oi" }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        ast = make_ast(src)
        v = ast.variables[0]
        assert v.type == 'text'
        assert v.value == 'oi'

    def test_plural_cardinality(self):
        src = '''\
program "T"
vars { lista: Text[] }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> lista { pass OK }
'''
        ast = make_ast(src)
        assert ast.variables[0].cardinality == 'plural'

    def test_logic_type(self):
        src = '''\
program "T"
vars { flag: Logic }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> flag { pass OK }
'''
        assert make_ast(src).variables[0].type == 'logic'

    def test_initial_numeric_value(self):
        src = '''\
program "T"
vars { n: Number = 42 }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> n { pass OK }
'''
        assert make_ast(src).variables[0].value == 42


# ---------------------------------------------------------------------------
# Procedimentos
# ---------------------------------------------------------------------------

class TestProcDecl:
    def test_proc_name(self):
        ast = make_ast(MINIMAL)
        assert ast.procedures[0].name == 'foo'

    def test_from_resolution_simple(self):
        ast = make_ast(MINIMAL)
        p = ast.procedures[0]
        assert p.library == 'Lib'
        assert p.macro == 'bar'

    def test_from_resolution_nested(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "Federal.@.GenJin" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        p = make_ast(src).procedures[0]
        assert p.library == 'Federal.@'
        assert p.macro == 'GenJin'

    def test_output_codes(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<5> } }
exec f() >> s { pass OK, ERR }
'''
        codes = make_ast(src).procedures[0].output_codes
        assert len(codes) == 2
        assert codes[0] == OutputCodeNode(name='OK', code=0)
        assert codes[1] == OutputCodeNode(name='ERR', code=5)

    def test_param_literal(self):
        src = '''\
program "T"
vars { s: Number }
procs { f(n: Number) from "A.b" { codes OK<0> } }
exec f(n=1) >> s { pass OK }
'''
        p = make_ast(src).procedures[0]
        assert len(p.parameters) == 1
        param = p.parameters[0]
        assert param.name == 'n'
        assert param.type == 'number'
        assert param.evaluation == 'literal'

    def test_param_reference(self):
        src = '''\
program "T"
vars {
    s: Number
    r: Text
}
procs { f(resp: &Text) from "A.b" { codes OK<0> } }
exec f(resp=&r) >> s { pass OK }
'''
        p = make_ast(src).procedures[0]
        param = p.parameters[0]
        assert param.evaluation == 'reference'


# ---------------------------------------------------------------------------
# Exec e Argumentos
# ---------------------------------------------------------------------------

class TestExecBlock:
    def test_kwarg_literal_number(self):
        src = '''\
program "T"
vars { s: Number }
procs { f(n: Number) from "A.b" { codes OK<0> } }
exec f(n=5) >> s { pass OK }
'''
        block = make_ast(src).block
        assert block.kwargs['n'] == ArgNode(value=5, evaluation='literal')

    def test_kwarg_literal_string(self):
        src = '''\
program "T"
vars { s: Number }
procs { f(msg: Text) from "A.b" { codes OK<0> } }
exec f(msg="hello") >> s { pass OK }
'''
        block = make_ast(src).block
        assert block.kwargs['msg'] == ArgNode(value='hello', evaluation='literal')

    def test_kwarg_reference(self):
        src = '''\
program "T"
vars {
    s: Number
    r: Text
}
procs { f(resp: &Text) from "A.b" { codes OK<0> } }
exec f(resp=&r) >> s { pass OK }
'''
        block = make_ast(src).block
        assert block.kwargs['resp'] == ArgNode(value='r', evaluation='reference')

    def test_no_variable_inherits_none(self):
        """Exec raiz sem >> resulta em variable=None."""
        src = '''\
program "T"
vars { }
procs { f() from "A.b" { codes OK<0> } }
exec f() { pass OK }
'''
        assert make_ast(src).block.variable is None

    def test_block_name_as(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f() as "meu_bloco" >> s { pass OK }
'''
        assert make_ast(src).block.block_name == 'meu_bloco'

    def test_block_name_default_none(self):
        assert make_ast(MINIMAL).block.block_name is None

    def test_while_codes(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<1> } }
exec f() >> s {
    pass OK
} while(ERR)
'''
        block = make_ast(src).block
        assert block.loop_while == ['ERR']
        assert 'OK' in block.pass_codes


# ---------------------------------------------------------------------------
# Herança de variável
# ---------------------------------------------------------------------------

class TestVariableInheritance:
    SRC = '''\
program "T"
vars { s: Number }
procs {
    outer() from "A.b" { codes X<0> }
    inner() from "A.c" { codes Y<0> }
}
exec outer() >> s {
    case X : exec inner() {
        pass Y
    }
}
'''

    def test_child_inherits_variable(self):
        ast = make_ast(self.SRC)
        child = ast.block.cases[0].block
        assert child.variable == 's'

    def test_child_can_override_variable(self):
        src = '''\
program "T"
vars {
    s: Number
    t: Number
}
procs {
    outer() from "A.b" { codes X<0> }
    inner() from "A.c" { codes Y<0> }
}
exec outer() >> s {
    case X : exec inner() >> t {
        pass Y
    }
}
'''
        ast = make_ast(src)
        child = ast.block.cases[0].block
        assert child.variable == 't'


# ---------------------------------------------------------------------------
# Validações semânticas
# ---------------------------------------------------------------------------

class TestSemanticValidation:

    # Regra 4: proc em exec deve estar declarado
    def test_undeclared_proc_raises(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec nao_existe() >> s { pass OK }
'''
        with pytest.raises(ParseError, match="nao_existe"):
            make_ast(src)

    # Regra 3: variável em >> deve estar declarada
    def test_undeclared_variable_in_arrow_raises(self):
        src = '''\
program "T"
vars { }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> nao_declarada { pass OK }
'''
        with pytest.raises(ParseError, match="nao_declarada"):
            make_ast(src)

    # Regra 3: variável em =& deve estar declarada
    def test_undeclared_variable_in_ref_arg_raises(self):
        src = '''\
program "T"
vars { s: Number }
procs { f(r: &Text) from "A.b" { codes OK<0> } }
exec f(r=&nao_declarada) >> s { pass OK }
'''
        with pytest.raises(ParseError, match="nao_declarada"):
            make_ast(src)

    # Regra 1 (relaxada): case aceita qualquer código, incluindo borbulhados de filhos
    def test_case_bubbled_code_accepted(self):
        """case com código não declarado no proc deve ser aceito (borbulhado de filho)."""
        src = '''\
program "T"
vars { s: Number }
procs {
    outer() from "A.b" { codes OK<0> }
    inner() from "A.c" { codes Y<0> }
}
exec outer() >> s {
    case OK : exec inner() { pass Y }
    case Y : exec inner() { pass Y }
}
'''
        prog = make_ast(src)
        assert len(prog.block.cases) == 2

    # Regra 1 (relaxada): while aceita qualquer código, incluindo borbulhados de filhos
    def test_while_bubbled_code_accepted(self):
        """while com código não declarado no proc deve ser aceito (borbulhado de filho)."""
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> s {
    pass OK
} while(OK, QUALQUER_CODIGO_FILHO)
'''
        prog = make_ast(src)
        assert prog.block.loop_while == ['OK', 'QUALQUER_CODIGO_FILHO']

    # Regra 2: pass deve cobrir códigos não tratados
    def test_unhandled_code_without_pass_raises(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<1> } }
exec f() >> s {
    pass OK
}
'''
        with pytest.raises(ParseError, match="ERR"):
            make_ast(src)

    # Regra 5: parâmetro &Type exige =& (referência), nunca literal
    def test_ref_param_with_literal_raises(self):
        src = '''\
program "T"
vars { s: Number }
procs { f(r: &Text) from "A.b" { codes OK<0> } }
exec f(r="literal") >> s { pass OK }
'''
        with pytest.raises(ParseError, match="referência"):
            make_ast(src)

    # Argumento com nome de parâmetro inexistente
    def test_unknown_kwarg_raises(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f(inexistente=1) >> s { pass OK }
'''
        with pytest.raises(ParseError, match="inexistente"):
            make_ast(src)

    # from sem ponto
    def test_from_without_dot_raises(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "semponto" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        with pytest.raises(ParseError, match="ponto"):
            make_ast(src)


# ---------------------------------------------------------------------------
# ParseError com linha
# ---------------------------------------------------------------------------

class TestParseErrorLine:
    def test_error_has_line(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec nao_existe() >> s { pass OK }
'''
        with pytest.raises(ParseError) as exc_info:
            make_ast(src)
        assert exc_info.value.line > 0

    def test_error_message_contains_linha(self):
        with pytest.raises(ParseError) as exc_info:
            make_ast('program')
        assert 'Linha' in str(exc_info.value)


# ---------------------------------------------------------------------------
# Integração: examples/basic.gnj
# ---------------------------------------------------------------------------

BASIC_GNJ = '''\
program "Sistema de Pagamento"

vars {
    status_var: Number
    status_var2: Number
    status_conexao: Text = "idle"
    res: Text
    minha_lista: Text[]
}

procs {
    verificar_rede() from "Net.check" {
        codes ONLINE<0>, OFFLINE<1>
    }

    esperar(segundos: Number) from "Sys.sleep" {
        codes DONE<0>, ERROR<5>
    }

    enviar(texto: Text, resposta: &Text) from "Sys.send" {
        codes OK<0>, TIMEOUT<10>
    }
}

exec verificar_rede() >> status_var {
    case OFFLINE : exec esperar(segundos=5) {
        case DONE : exec enviar(texto="OK", resposta=&res) >> status_var2 {
            pass OK, TIMEOUT
        }
    } while(ERROR)
    pass ONLINE, OK, TIMEOUT
}
'''


class TestBasicGnj:
    def test_parses_without_error(self):
        ast = make_ast(BASIC_GNJ)
        assert isinstance(ast, ProgramNode)

    def test_program_name(self):
        assert make_ast(BASIC_GNJ).name == 'Sistema de Pagamento'

    def test_five_variables(self):
        assert len(make_ast(BASIC_GNJ).variables) == 5

    def test_three_procs(self):
        assert len(make_ast(BASIC_GNJ).procedures) == 3

    def test_verificar_rede_from(self):
        p = make_ast(BASIC_GNJ).procedures[0]
        assert p.library == 'Net'
        assert p.macro == 'check'

    def test_enviar_ref_param(self):
        p = make_ast(BASIC_GNJ).procedures[2]
        ref_param = next(pm for pm in p.parameters if pm.name == 'resposta')
        assert ref_param.evaluation == 'reference'

    def test_root_exec(self):
        block = make_ast(BASIC_GNJ).block
        assert block.proc_name == 'verificar_rede'
        assert block.variable == 'status_var'

    def test_nested_case_offline(self):
        block = make_ast(BASIC_GNJ).block
        assert len(block.cases) == 1
        assert block.cases[0].output_code == 'OFFLINE'

    def test_while_error(self):
        block = make_ast(BASIC_GNJ).block
        inner = block.cases[0].block
        assert 'ERROR' in inner.loop_while

    def test_deep_nested_exec(self):
        block = make_ast(BASIC_GNJ).block
        esperar_block = block.cases[0].block
        enviar_block = esperar_block.cases[0].block
        assert enviar_block.proc_name == 'enviar'
        assert enviar_block.variable == 'status_var2'

    def test_enviar_resposta_ref_arg(self):
        block = make_ast(BASIC_GNJ).block
        esperar_block = block.cases[0].block
        enviar_block = esperar_block.cases[0].block
        arg = enviar_block.kwargs['resposta']
        assert arg == ArgNode(value='res', evaluation='reference')

    def test_root_pass_codes(self):
        block = make_ast(BASIC_GNJ).block
        assert set(block.pass_codes) == {'ONLINE', 'OK', 'TIMEOUT'}

    def test_esperar_inherits_variable(self):
        block = make_ast(BASIC_GNJ).block
        esperar_block = block.cases[0].block
        # esperar não tem >>, herda status_var do pai
        assert esperar_block.variable == 'status_var'


# ---------------------------------------------------------------------------
# B-013: keyword 'proc' não é mais aceita dentro de procs { }
# ---------------------------------------------------------------------------

class TestProcKeywordRemoved:
    def test_proc_keyword_raises(self):
        src = '''\
program "T"
vars { s: Number }
procs { proc f() from "A.b" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        with pytest.raises(ParseError, match="proc"):
            make_ast(src)

    def test_without_proc_keyword_ok(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        assert make_ast(src).procedures[0].name == 'f'


# ---------------------------------------------------------------------------
# B-012: ordem `as` deve vir antes de `>>`
# ---------------------------------------------------------------------------

class TestAsBeforeArrow:
    def test_as_before_arrow_ok(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f() as "nome" >> s { pass OK }
'''
        ast = make_ast(src)
        assert ast.block.block_name == 'nome'
        assert ast.block.variable == 's'

    def test_arrow_before_as_raises(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> s as "nome" { pass OK }
'''
        with pytest.raises(ParseError, match="as"):
            make_ast(src)

    def test_only_as_no_arrow_ok(self):
        src = '''\
program "T"
vars { }
procs { f() from "A.b" { codes OK<0> } }
exec f() as "nome" { pass OK }
'''
        assert make_ast(src).block.block_name == 'nome'

    def test_only_arrow_no_as_ok(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        assert make_ast(src).block.variable == 's'


# ---------------------------------------------------------------------------
# B-014: ordem flexível dos blocos vars / procs / exec
# ---------------------------------------------------------------------------

class TestFlexibleBlockOrder:
    BASE = '''\
program "T"
{vars}
{procs}
{exec}
'''
    VARS = 'vars { s: Number }'
    PROCS = 'procs { f() from "A.b" { codes OK<0> } }'
    EXEC = 'exec f() >> s { pass OK }'

    def _src(self, order):
        blocks = {'vars': self.VARS, 'procs': self.PROCS, 'exec': self.EXEC}
        return 'program "T"\n' + '\n'.join(blocks[k] for k in order) + '\n'

    def test_vars_procs_exec(self):
        assert make_ast(self._src(['vars', 'procs', 'exec'])).name == 'T'

    def test_procs_vars_exec(self):
        assert make_ast(self._src(['procs', 'vars', 'exec'])).name == 'T'

    def test_vars_exec_procs(self):
        assert make_ast(self._src(['vars', 'exec', 'procs'])).name == 'T'

    def test_procs_exec_vars(self):
        assert make_ast(self._src(['procs', 'exec', 'vars'])).name == 'T'

    def test_exec_vars_procs(self):
        assert make_ast(self._src(['exec', 'vars', 'procs'])).name == 'T'

    def test_exec_procs_vars(self):
        assert make_ast(self._src(['exec', 'procs', 'vars'])).name == 'T'

    def test_duplicate_vars_raises(self):
        src = 'program "T"\nvars { s: Number }\nvars { t: Number }\nprocs { f() from "A.b" { codes OK<0> } }\nexec f() >> s { pass OK }\n'
        with pytest.raises(ParseError, match="vars"):
            make_ast(src)

    def test_duplicate_procs_raises(self):
        src = 'program "T"\nvars { s: Number }\nprocs { f() from "A.b" { codes OK<0> } }\nprocs { f() from "A.b" { codes OK<0> } }\nexec f() >> s { pass OK }\n'
        with pytest.raises(ParseError, match="procs"):
            make_ast(src)

    def test_missing_vars_raises(self):
        src = 'program "T"\nprocs { f() from "A.b" { codes OK<0> } }\nexec f() { pass OK }\n'
        with pytest.raises(ParseError, match="vars"):
            make_ast(src)

    def test_missing_procs_raises(self):
        src = 'program "T"\nvars { s: Number }\nexec f() >> s { pass OK }\n'
        with pytest.raises(ParseError):
            make_ast(src)


# ---------------------------------------------------------------------------
# B-015: notação inline @proc() e @proc() when(CODE)
# ---------------------------------------------------------------------------

_INLINE_BASE = '''\
program "T"
vars {{ s: Number }}
procs {{ f() from "A.b" {{ codes OK<0>, ERR<1> }} }}
{exec}
'''


def _inline_src(exec_block: str) -> str:
    return _INLINE_BASE.format(exec=exec_block)


class TestInlineParsing:
    """Testes de parsing da notação inline — B-015."""

    # --- Tipo 1: átomo simples @proc() ---

    def test_tipo1_root_returns_inline_seq(self):
        """@proc() na raiz produz InlineSeqNode com terminal InlineAtomNode."""
        src = _inline_src('@f() >> s')
        ast = make_ast(src)
        assert isinstance(ast.block, InlineSeqNode)

    def test_tipo1_root_no_chained(self):
        src = _inline_src('@f() >> s')
        ast = make_ast(src)
        assert ast.block.chained == []

    def test_tipo1_root_terminal_proc(self):
        src = _inline_src('@f() >> s')
        ast = make_ast(src)
        assert isinstance(ast.block.terminal, InlineAtomNode)
        assert ast.block.terminal.proc_name == 'f'

    def test_tipo1_root_terminal_variable(self):
        src = _inline_src('@f() >> s')
        ast = make_ast(src)
        assert ast.block.terminal.variable == 's'
        assert ast.block.terminal.variable_explicit is True

    def test_tipo1_root_no_when(self):
        src = _inline_src('@f() >> s')
        ast = make_ast(src)
        assert ast.block.terminal.when_code is None

    def test_tipo1_root_with_while(self):
        src = _inline_src('@f() >> s while(ERR)')
        ast = make_ast(src)
        assert ast.block.terminal.while_code == 'ERR'

    def test_tipo1_root_no_while(self):
        src = _inline_src('@f() >> s')
        ast = make_ast(src)
        assert ast.block.terminal.while_code is None

    # --- Tipo 2: átomo encadeado @proc() when(CODE) ---

    def test_tipo2_two_atoms_returns_inline_seq(self):
        """@f() when(OK) + @f() — dois átomos produz InlineSeqNode com 1 chained."""
        src = _inline_src('@f() when(OK)\n@f() >> s')
        ast = make_ast(src)
        assert isinstance(ast.block, InlineSeqNode)
        assert len(ast.block.chained) == 1

    def test_tipo2_chained_atom_when_code(self):
        src = _inline_src('@f() when(OK)\n@f() >> s')
        ast = make_ast(src)
        assert ast.block.chained[0].when_code == 'OK'

    def test_tipo2_terminal_is_inline_atom(self):
        src = _inline_src('@f() when(OK)\n@f() >> s')
        ast = make_ast(src)
        assert isinstance(ast.block.terminal, InlineAtomNode)
        assert ast.block.terminal.when_code is None

    def test_tipo2_three_atoms(self):
        """Três átomos: dois chained + terminal."""
        src = _inline_src('@f() when(OK)\n@f() when(ERR)\n@f() >> s')
        ast = make_ast(src)
        assert len(ast.block.chained) == 2
        assert ast.block.chained[0].when_code == 'OK'
        assert ast.block.chained[1].when_code == 'ERR'
        assert ast.block.terminal.when_code is None

    def test_tipo2_chained_with_while(self):
        """Átomo encadeado pode ter while antes de when."""
        src = _inline_src('@f() while(ERR) when(OK)\n@f() >> s')
        ast = make_ast(src)
        assert ast.block.chained[0].while_code == 'ERR'
        assert ast.block.chained[0].when_code == 'OK'

    # --- Inline dentro de case ---

    def test_inline_in_case_body(self):
        """Inline aceito como body de case."""
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<1> } }
exec f() >> s {
    case OK: @f()
    pass ERR
}
'''
        ast = make_ast(src)
        assert isinstance(ast.block.cases[0].block, InlineSeqNode)

    def test_inline_chain_in_case_body(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<1> } }
exec f() >> s {
    case OK: @f() when(OK)
             @f()
    pass ERR
}
'''
        ast = make_ast(src)
        assert isinstance(ast.block.cases[0].block, InlineSeqNode)
        assert len(ast.block.cases[0].block.chained) == 1

    # --- Terminal canônico exec como terminal da inline_seq ---

    def test_canonical_exec_terminal(self):
        """Inline seq pode terminar com exec canônico."""
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
        ast = make_ast(src)
        seq = ast.block.cases[0].block
        assert isinstance(seq, InlineSeqNode)
        assert isinstance(seq.terminal, ExecBlockNode)

    # --- Erros de semântica ---

    def test_unknown_proc_raises(self):
        """Proc não declarado em inline atom deve levantar ParseError."""
        src = _inline_src('@unknown() >> s')
        with pytest.raises(ParseError, match="'unknown' não declarado"):
            make_ast(src)

    def test_unknown_variable_raises(self):
        """Variável não declarada em >> deve levantar ParseError."""
        src = _inline_src('@f() >> x')
        with pytest.raises(ParseError, match="'x' não declarada"):
            make_ast(src)

    def test_unknown_when_code_raises(self):
        """Código desconhecido em when deve levantar ParseError."""
        src = _inline_src('@f() when(BOGUS)\n@f() >> s')
        with pytest.raises(ParseError, match="'BOGUS'"):
            make_ast(src)

    def test_unknown_while_code_raises(self):
        """Código desconhecido em while do inline atom deve levantar ParseError."""
        src = _inline_src('@f() while(BOGUS) when(OK)\n@f() >> s')
        with pytest.raises(ParseError, match="'BOGUS'"):
            make_ast(src)

