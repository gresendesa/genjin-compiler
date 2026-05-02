"""
Testes unitários do Transpiler — Etapa 3 do compilador Genjin.

Cobre:
  - Estrutura do template gerado (imports, set program, build)
  - Mapeamento de variáveis (tipo, cardinalidade, valor inicial)
  - Mapeamento de procedimentos (ATTRIBUTE.MACRO como lista, parâmetros, códigos)
  - Mapeamento de blocos exec (ATTRIBUTE.PROCEDURE, CASES, LOOP_WHILE, PASS_CODES)
  - ATTRIBUTE.VARIABLE ausente em blocos sem >> (herança)
  - ATTRIBUTE.VARIABLE presente em blocos com >>
  - Teste de integração: template gerado de basic.gnj é Jinja2 válido
"""

import pytest
from compiler.transpiler import transpile, Transpiler
from compiler.parser import parse


def gen(source: str) -> str:
    return transpile(source)


# ---------------------------------------------------------------------------
# Programa mínimo
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


class TestMinimalTemplate:
    def test_has_import_line(self):
        out = gen(MINIMAL)
        assert '{* from "genjin" import ATTRIBUTE, TYPE, CARDINALITY, EVALUATION, MACROMOD, build *}' in out

    def test_has_set_program(self):
        out = gen(MINIMAL)
        assert 'set program' in out

    def test_has_build_call(self):
        out = gen(MINIMAL)
        assert '{{ build(prog=program, language_renderer=MACROMOD) }}' in out

    def test_has_program_name(self):
        out = gen(MINIMAL)
        assert "'Minimo'" in out

    def test_has_attribute_name_key(self):
        out = gen(MINIMAL)
        assert 'ATTRIBUTE.NAME' in out

    def test_has_attribute_variables_key(self):
        out = gen(MINIMAL)
        assert 'ATTRIBUTE.VARIABLES' in out

    def test_has_attribute_procedures_key(self):
        out = gen(MINIMAL)
        assert 'ATTRIBUTE.PROCEDURES' in out

    def test_has_attribute_block_key(self):
        out = gen(MINIMAL)
        assert 'ATTRIBUTE.BLOCK' in out


# ---------------------------------------------------------------------------
# Variáveis
# ---------------------------------------------------------------------------

class TestVarMapping:
    def test_number_type(self):
        out = gen(MINIMAL)
        assert 'TYPE.NUMBER' in out

    def test_singular_cardinality(self):
        out = gen(MINIMAL)
        assert 'CARDINALITY.SINGULAR' in out

    def test_plural_cardinality(self):
        src = '''\
program "T"
vars { lista: Text[] }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> lista { pass OK }
'''
        assert 'CARDINALITY.PLURAL' in gen(src)

    def test_text_type(self):
        src = '''\
program "T"
vars { s: Text = "oi" }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        assert 'TYPE.TEXT' in gen(src)

    def test_logic_type(self):
        src = '''\
program "T"
vars { flag: Logic }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> flag { pass OK }
'''
        assert 'TYPE.LOGIC' in gen(src)

    def test_initial_string_value(self):
        src = '''\
program "T"
vars { s: Text = "idle" }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        out = gen(src)
        assert 'ATTRIBUTE.VALUE' in out
        assert "'idle'" in out

    def test_initial_numeric_value(self):
        src = '''\
program "T"
vars { n: Number = 42 }
procs { f() from "A.b" { codes OK<0> } }
exec f() >> n { pass OK }
'''
        out = gen(src)
        assert 'ATTRIBUTE.VALUE' in out
        assert '42' in out

    def test_no_value_no_attribute_value(self):
        out = gen(MINIMAL)
        # Variável 's' sem valor inicial não deve ter ATTRIBUTE.VALUE
        # (mas confirma que não há ATTRIBUTE.VALUE no template mínimo)
        lines_with_value = [l for l in out.splitlines() if 'ATTRIBUTE.VALUE' in l]
        assert len(lines_with_value) == 0


# ---------------------------------------------------------------------------
# Procedimentos
# ---------------------------------------------------------------------------

class TestProcMapping:
    def test_macro_as_list(self):
        out = gen(MINIMAL)
        # ATTRIBUTE.MACRO deve ser uma lista ['Lib', 'bar']
        assert "['Lib', 'bar']" in out

    def test_macro_nested_library(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "Federal.@.GenJin" { codes OK<0> } }
exec f() >> s { pass OK }
'''
        out = gen(src)
        assert "'Federal.@'" in out
        assert "'GenJin'" in out

    def test_output_codes_present(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<5> } }
exec f() >> s { pass OK, ERR }
'''
        out = gen(src)
        assert 'ATTRIBUTE.OUTPUT_CODES' in out
        assert "'OK'" in out
        assert "'ERR'" in out
        assert '5' in out

    def test_param_literal_evaluation(self):
        src = '''\
program "T"
vars { s: Number }
procs { f(n: Number) from "A.b" { codes OK<0> } }
exec f(n=1) >> s { pass OK }
'''
        out = gen(src)
        assert 'EVALUATION.LITERAL' in out
        assert 'ATTRIBUTE.PARAMETERS' in out

    def test_param_reference_evaluation(self):
        src = '''\
program "T"
vars { s: Number
       r: Text }
procs { f(resp: &Text) from "A.b" { codes OK<0> } }
exec f(resp=&r) >> s { pass OK }
'''
        out = gen(src)
        assert 'EVALUATION.REFERENCE' in out


# ---------------------------------------------------------------------------
# Bloco exec
# ---------------------------------------------------------------------------

class TestBlockMapping:
    def test_attribute_variable_present_when_explicit(self):
        out = gen(MINIMAL)
        assert 'ATTRIBUTE.VARIABLE' in out
        assert "'s'" in out

    def test_attribute_variable_absent_when_inherited(self):
        src = '''\
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
        out = gen(src)
        lines = out.splitlines()
        # ATTRIBUTE.VARIABLE: (sem o S final) — só o exec raiz deve ter
        var_lines = [l for l in lines if 'ATTRIBUTE.VARIABLE:' in l and 'ATTRIBUTE.VARIABLES' not in l]
        assert len(var_lines) == 1

    def test_attribute_variable_present_when_overriding(self):
        src = '''\
program "T"
vars { s: Number
       t: Number }
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
        out = gen(src)
        lines = out.splitlines()
        var_lines = [l for l in lines if 'ATTRIBUTE.VARIABLE:' in l and 'ATTRIBUTE.VARIABLES' not in l]
        # Dois execs com >>, dois ATTRIBUTE.VARIABLE
        assert len(var_lines) == 2

    def test_attribute_cases_present(self):
        out = gen(MINIMAL)
        assert 'ATTRIBUTE.CASES' in out

    def test_attribute_pass_codes_present(self):
        out = gen(MINIMAL)
        assert 'ATTRIBUTE.PASS_CODES' in out

    def test_attribute_loop_while_present(self):
        out = gen(MINIMAL)
        assert 'ATTRIBUTE.LOOP_WHILE' in out

    def test_while_codes_in_output(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0>, ERR<1> } }
exec f() >> s {
    pass OK
} while(ERR)
'''
        out = gen(src)
        assert 'ATTRIBUTE.LOOP_WHILE' in out
        assert "'ERR'" in out

    def test_block_name_as(self):
        src = '''\
program "T"
vars { s: Number }
procs { f() from "A.b" { codes OK<0> } }
exec f() as "meu_bloco" >> s { pass OK }
'''
        out = gen(src)
        assert "'meu_bloco'" in out

    def test_block_name_defaults_to_proc_name(self):
        out = gen(MINIMAL)
        # Sem 'as', o nome do bloco é o nome do proc ('foo')
        assert "'foo'" in out

    def test_kwarg_literal_in_output(self):
        src = '''\
program "T"
vars { s: Number }
procs { f(n: Number) from "A.b" { codes OK<0> } }
exec f(n=7) >> s { pass OK }
'''
        out = gen(src)
        assert 'ATTRIBUTE.KEYWORD_ARGS' in out
        assert "'n'" in out
        assert '7' in out
        assert 'EVALUATION.LITERAL' in out

    def test_kwarg_reference_in_output(self):
        src = '''\
program "T"
vars { s: Number
       r: Text }
procs { f(resp: &Text) from "A.b" { codes OK<0> } }
exec f(resp=&r) >> s { pass OK }
'''
        out = gen(src)
        assert 'ATTRIBUTE.KEYWORD_ARGS' in out
        assert "'resp'" in out
        assert "'r'" in out
        assert 'EVALUATION.REFERENCE' in out


# ---------------------------------------------------------------------------
# Integração: basic.gnj → template Jinja2 válido
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


class TestBasicGnjTranspiler:
    def test_transpiles_without_error(self):
        out = transpile(BASIC_GNJ)
        assert isinstance(out, str)
        assert len(out) > 0

    def test_contains_program_name(self):
        out = transpile(BASIC_GNJ)
        assert "'Sistema de Pagamento'" in out

    def test_contains_net_check_macro(self):
        out = transpile(BASIC_GNJ)
        assert "'Net'" in out
        assert "'check'" in out

    def test_root_variable_present(self):
        out = transpile(BASIC_GNJ)
        assert "'status_var'" in out

    def test_status_var2_present(self):
        # status_var2 tem >> explícito (no exec enviar)
        out = transpile(BASIC_GNJ)
        assert "'status_var2'" in out

    def test_error_in_loop_while(self):
        out = transpile(BASIC_GNJ)
        # 'ERROR' deve aparecer em ATTRIBUTE.LOOP_WHILE
        lines = out.splitlines()
        while_lines = [l for l in lines if 'ATTRIBUTE.LOOP_WHILE' in l]
        assert any("'ERROR'" in l for l in while_lines)

    def test_initial_value_idle(self):
        out = transpile(BASIC_GNJ)
        assert "'idle'" in out

    def test_pass_codes_root(self):
        out = transpile(BASIC_GNJ)
        assert "'ONLINE'" in out
        assert "'OK'" in out
        assert "'TIMEOUT'" in out

    def test_jinja2_syntax_valid(self):
        """Template gerado deve ser válido Jinja2 (configurado com delimitadores do projeto)."""
        from jinja2 import Environment
        out = transpile(BASIC_GNJ)
        env = Environment(
            block_start_string='{*',
            block_end_string='*}',
            variable_start_string='{{',
            variable_end_string='}}',
            comment_start_string='{!!',
            comment_end_string='!!}',
        )
        # parse() do Jinja2 lança exceção se a sintaxe for inválida
        env.parse(out)

    def test_esperar_block_no_variable(self):
        """esperar não tem >>, então ATTRIBUTE.VARIABLE não deve aparecer no bloco dele."""
        out = transpile(BASIC_GNJ)
        lines = out.splitlines()
        var_lines = [l for l in lines if 'ATTRIBUTE.VARIABLE:' in l and 'ATTRIBUTE.VARIABLES' not in l]
        # status_var (raiz) + status_var2 (enviar) = 2
        assert len(var_lines) == 2
