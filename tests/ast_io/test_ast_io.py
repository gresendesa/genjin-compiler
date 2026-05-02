"""
Testes de serialização/desserialização da AST — compiler/ast_io.py

Cobre:
  - tokens_to_json / tokens_from_json: round-trip fiel
  - ast_to_json / ast_from_json: round-trip fiel com basic.gnj
  - Preservação de tipos: bool, int, str, None
  - Nós aninhados recursivos (ExecBlockNode → CaseNode → ExecBlockNode)
  - Nó raiz deve ser ProgramNode
  - JSON inválido levanta erro
"""

import json
import pytest

from compiler.scanner import Scanner, Token, TokenType
from compiler.parser import (
    parse, ProgramNode, ExecBlockNode, CaseNode,
    ArgNode, VarDeclNode, ProcDeclNode,
)
from compiler.ast_io import (
    tokens_to_json, tokens_from_json,
    ast_to_json, ast_from_json,
)


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


# ---------------------------------------------------------------------------
# Tokens round-trip
# ---------------------------------------------------------------------------

class TestTokensRoundTrip:
    def _tokens(self, source: str = 'program "T"') -> list[Token]:
        return Scanner(source).tokenize()

    def test_to_json_is_string(self):
        assert isinstance(tokens_to_json(self._tokens()), str)

    def test_to_json_is_valid_json(self):
        json.loads(tokens_to_json(self._tokens()))

    def test_round_trip_type(self):
        toks = self._tokens()
        restored = tokens_from_json(tokens_to_json(toks))
        assert [t.type for t in restored] == [t.type for t in toks]

    def test_round_trip_value(self):
        toks = self._tokens()
        restored = tokens_from_json(tokens_to_json(toks))
        assert [t.value for t in restored] == [t.value for t in toks]

    def test_round_trip_line(self):
        toks = self._tokens('foo\nbar')
        restored = tokens_from_json(tokens_to_json(toks))
        assert [t.line for t in restored] == [t.line for t in toks]

    def test_round_trip_basic_gnj(self):
        toks = Scanner(BASIC_GNJ).tokenize()
        restored = tokens_from_json(tokens_to_json(toks))
        assert len(restored) == len(toks)
        for orig, rest in zip(toks, restored):
            assert orig.type == rest.type
            assert orig.value == rest.value
            assert orig.line == rest.line

    def test_eof_preserved(self):
        toks = self._tokens()
        restored = tokens_from_json(tokens_to_json(toks))
        assert restored[-1].type == TokenType.EOF


# ---------------------------------------------------------------------------
# AST round-trip
# ---------------------------------------------------------------------------

class TestAstRoundTrip:
    def _ast(self, source: str = BASIC_GNJ) -> ProgramNode:
        return parse(source)

    def test_to_json_is_string(self):
        assert isinstance(ast_to_json(self._ast()), str)

    def test_to_json_is_valid_json(self):
        json.loads(ast_to_json(self._ast()))

    def test_round_trip_returns_program_node(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert isinstance(restored, ProgramNode)

    def test_round_trip_program_name(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert restored.name == ast.name

    def test_round_trip_variables_count(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert len(restored.variables) == len(ast.variables)

    def test_round_trip_variable_fields(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        for orig, rest in zip(ast.variables, restored.variables):
            assert orig.name == rest.name
            assert orig.type == rest.type
            assert orig.cardinality == rest.cardinality
            assert orig.value == rest.value

    def test_round_trip_procs_count(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert len(restored.procedures) == len(ast.procedures)

    def test_round_trip_proc_macro(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        for orig, rest in zip(ast.procedures, restored.procedures):
            assert orig.library == rest.library
            assert orig.macro == rest.macro

    def test_round_trip_proc_output_codes(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        for orig_p, rest_p in zip(ast.procedures, restored.procedures):
            for orig_c, rest_c in zip(orig_p.output_codes, rest_p.output_codes):
                assert orig_c.name == rest_c.name
                assert orig_c.code == rest_c.code

    def test_round_trip_proc_params(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        for orig_p, rest_p in zip(ast.procedures, restored.procedures):
            for orig_pm, rest_pm in zip(orig_p.parameters, rest_p.parameters):
                assert orig_pm.name == rest_pm.name
                assert orig_pm.evaluation == rest_pm.evaluation

    def test_round_trip_block_proc_name(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert restored.block.proc_name == ast.block.proc_name

    def test_round_trip_block_variable(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert restored.block.variable == ast.block.variable

    def test_round_trip_block_variable_explicit(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert restored.block.variable_explicit == ast.block.variable_explicit

    def test_round_trip_bool_type_preserved(self):
        """variable_explicit é bool — deve sobreviver ao JSON como bool, não int."""
        ast = self._ast()
        j = ast_to_json(ast)
        restored = ast_from_json(j)
        assert isinstance(restored.block.variable_explicit, bool)

    def test_round_trip_nested_cases(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert len(restored.block.cases) == len(ast.block.cases)
        case_orig = ast.block.cases[0]
        case_rest = restored.block.cases[0]
        assert case_rest.output_code == case_orig.output_code
        assert isinstance(case_rest.block, ExecBlockNode)

    def test_round_trip_deep_nested_exec(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        # exec esperar → case DONE → exec enviar
        enviar_orig = ast.block.cases[0].block.cases[0].block
        enviar_rest = restored.block.cases[0].block.cases[0].block
        assert enviar_rest.proc_name == enviar_orig.proc_name
        assert enviar_rest.variable == enviar_orig.variable

    def test_round_trip_kwargs(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        # exec enviar tem kwarg resposta=&res (reference)
        enviar_orig = ast.block.cases[0].block.cases[0].block
        enviar_rest = restored.block.cases[0].block.cases[0].block
        assert enviar_rest.kwargs['resposta'].value == enviar_orig.kwargs['resposta'].value
        assert enviar_rest.kwargs['resposta'].evaluation == enviar_orig.kwargs['resposta'].evaluation

    def test_round_trip_kwarg_int_value(self):
        """Argumento literal numérico deve ser int após round-trip."""
        src = '''\
program "T"
vars { s: Number }
procs { f(n: Number) from "A.b" { codes OK<0> } }
exec f(n=7) >> s { pass OK }
'''
        ast = parse(src)
        restored = ast_from_json(ast_to_json(ast))
        assert restored.block.kwargs['n'].value == 7
        assert isinstance(restored.block.kwargs['n'].value, int)

    def test_round_trip_none_value(self):
        """Variável sem valor inicial deve ser None após round-trip."""
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        var = next(v for v in restored.variables if v.name == 'status_var')
        assert var.value is None

    def test_round_trip_string_initial_value(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        var = next(v for v in restored.variables if v.name == 'status_conexao')
        assert var.value == 'idle'

    def test_round_trip_loop_while(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        esperar_orig = ast.block.cases[0].block
        esperar_rest = restored.block.cases[0].block
        assert esperar_rest.loop_while == esperar_orig.loop_while

    def test_round_trip_pass_codes(self):
        ast = self._ast()
        restored = ast_from_json(ast_to_json(ast))
        assert set(restored.block.pass_codes) == set(ast.block.pass_codes)


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------

class TestAstIoErrors:
    def test_ast_from_invalid_json_raises(self):
        with pytest.raises((json.JSONDecodeError, Exception)):
            ast_from_json("não é json")

    def test_ast_from_wrong_root_raises(self):
        # raiz com __type__ diferente de ProgramNode
        wrong = json.dumps({"__type__": "ArgNode", "value": 1, "evaluation": "literal"})
        with pytest.raises(ValueError, match="ProgramNode"):
            ast_from_json(wrong)

    def test_ast_from_unknown_type_raises(self):
        bad = json.dumps({"__type__": "TipoInexistente", "foo": 1})
        with pytest.raises(ValueError, match="TipoInexistente"):
            ast_from_json(bad)
