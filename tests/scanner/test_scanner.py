"""
Testes unitários do Scanner — Etapa 1 do compilador Genjin.

Cobre:
  - Todos os token types definidos em TokenType
  - Precedência de >> sobre >
  - Comentários // e /* */ ignorados
  - Strings, números e identificadores
  - Rastreamento de número de linha
  - Erros para caracteres inválidos e strings/comentários não fechados
"""

import pytest
from compiler.scanner import Scanner, Token, TokenType, ScannerError


def scan(source: str) -> list[Token]:
    return Scanner(source).tokenize()


def types(source: str) -> list[TokenType]:
    return [t.type for t in scan(source) if t.type != TokenType.EOF]


def values(source: str) -> list[str]:
    return [t.value for t in scan(source) if t.type != TokenType.EOF]


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

class TestKeywords:
    def test_program(self):
        assert types('program') == [TokenType.KW_PROGRAM]

    def test_vars(self):
        assert types('vars') == [TokenType.KW_VARS]

    def test_procs(self):
        assert types('procs') == [TokenType.KW_PROCS]

    def test_proc(self):
        assert types('proc') == [TokenType.IDENT]

    def test_from(self):
        assert types('from') == [TokenType.KW_FROM]

    def test_exec(self):
        assert types('exec') == [TokenType.KW_EXEC]

    def test_case(self):
        assert types('case') == [TokenType.KW_CASE]

    def test_pass(self):
        assert types('pass') == [TokenType.KW_PASS]

    def test_while(self):
        assert types('while') == [TokenType.KW_WHILE]

    def test_as(self):
        assert types('as') == [TokenType.KW_AS]

    def test_codes(self):
        assert types('codes') == [TokenType.KW_CODES]

    def test_when(self):
        assert types('when') == [TokenType.KW_WHEN]

    def test_all_keywords_sequence(self):
        src = 'program vars procs from exec case pass while as codes when'
        expected = [
            TokenType.KW_PROGRAM, TokenType.KW_VARS, TokenType.KW_PROCS,
            TokenType.KW_FROM, TokenType.KW_EXEC,
            TokenType.KW_CASE, TokenType.KW_PASS, TokenType.KW_WHILE,
            TokenType.KW_AS, TokenType.KW_CODES, TokenType.KW_WHEN,
        ]
        assert types(src) == expected


# ---------------------------------------------------------------------------
# Tipos primitivos
# ---------------------------------------------------------------------------

class TestPrimitiveTypes:
    def test_number_type(self):
        assert types('Number') == [TokenType.TYPE_NUMBER]

    def test_text_type(self):
        assert types('Text') == [TokenType.TYPE_TEXT]

    def test_logic_type(self):
        assert types('Logic') == [TokenType.TYPE_LOGIC]


# ---------------------------------------------------------------------------
# Símbolos
# ---------------------------------------------------------------------------

class TestSymbols:
    def test_braces(self):
        assert types('{}') == [TokenType.LBRACE, TokenType.RBRACE]

    def test_parens(self):
        assert types('()') == [TokenType.LPAREN, TokenType.RPAREN]

    def test_angles(self):
        assert types('<>') == [TokenType.LANGLE, TokenType.RANGLE]

    def test_brackets(self):
        assert types('[]') == [TokenType.LBRACKET, TokenType.RBRACKET]

    def test_colon(self):
        assert types(':') == [TokenType.COLON]

    def test_comma(self):
        assert types(',') == [TokenType.COMMA]

    def test_ampersand(self):
        assert types('&') == [TokenType.AMPERSAND]

    def test_assign(self):
        assert types('=') == [TokenType.ASSIGN]

    def test_rangle_solo(self):
        assert types('>') == [TokenType.RANGLE]

    def test_arrow(self):
        assert types('>>') == [TokenType.ARROW]

    def test_arrow_precedence_over_rangle(self):
        """>> deve ser reconhecido como ARROW, não dois RANGLE."""
        toks = [t for t in scan('>>') if t.type != TokenType.EOF]
        assert len(toks) == 1
        assert toks[0].type == TokenType.ARROW

    def test_rangle_followed_by_rangle(self):
        """Dois > separados devem ser dois RANGLE."""
        assert types('> >') == [TokenType.RANGLE, TokenType.RANGLE]

    def test_arrow_in_context(self):
        """>> em contexto de exec deve ser ARROW."""
        toks = types('exec foo() >> status_var')
        assert TokenType.ARROW in toks
        assert toks.count(TokenType.RANGLE) == 0


# ---------------------------------------------------------------------------
# Notação inline — AT e KW_WHEN (B-015)
# ---------------------------------------------------------------------------

class TestInlineNotation:
    def test_at_token(self):
        assert types('@') == [TokenType.AT]

    def test_at_value(self):
        toks = [t for t in scan('@') if t.type != TokenType.EOF]
        assert toks[0].value == '@'

    def test_when_keyword(self):
        assert types('when') == [TokenType.KW_WHEN]

    def test_when_not_ident(self):
        """'when' deve ser KW_WHEN, não IDENT."""
        assert types('when') != [TokenType.IDENT]

    def test_inline_atom_tipo1(self):
        """@proc() >> var while(CODE) — sequência de tokens esperada."""
        src = '@inicia_processo() >> status_var while(ERROR)'
        expected = [
            TokenType.AT, TokenType.IDENT, TokenType.LPAREN, TokenType.RPAREN,
            TokenType.ARROW, TokenType.IDENT,
            TokenType.KW_WHILE, TokenType.LPAREN, TokenType.IDENT, TokenType.RPAREN,
        ]
        assert types(src) == expected

    def test_inline_atom_tipo2(self):
        """@proc() while(W) when(CODE) — tokens incluindo KW_WHEN."""
        src = '@inicia_processo() while(ERROR) when(OK)'
        expected = [
            TokenType.AT, TokenType.IDENT, TokenType.LPAREN, TokenType.RPAREN,
            TokenType.KW_WHILE, TokenType.LPAREN, TokenType.IDENT, TokenType.RPAREN,
            TokenType.KW_WHEN, TokenType.LPAREN, TokenType.IDENT, TokenType.RPAREN,
        ]
        assert types(src) == expected

    def test_at_followed_by_ident(self):
        """@ seguido de identificador."""
        toks = [t for t in scan('@proc') if t.type != TokenType.EOF]
        assert toks[0].type == TokenType.AT
        assert toks[1].type == TokenType.IDENT
        assert toks[1].value == 'proc'

    def test_when_as_ident_in_code(self):
        """'when' como código de saída não seria válido — é reservado como KW_WHEN."""
        assert types('when') == [TokenType.KW_WHEN]


# ---------------------------------------------------------------------------
# Literais
# ---------------------------------------------------------------------------

class TestLiterals:
    def test_string_simple(self):
        toks = [t for t in scan('"hello"') if t.type != TokenType.EOF]
        assert toks[0].type == TokenType.STRING
        assert toks[0].value == 'hello'

    def test_string_with_spaces(self):
        toks = [t for t in scan('"Sistema de Pagamento"') if t.type != TokenType.EOF]
        assert toks[0].value == 'Sistema de Pagamento'

    def test_string_empty(self):
        toks = [t for t in scan('""') if t.type != TokenType.EOF]
        assert toks[0].type == TokenType.STRING
        assert toks[0].value == ''

    def test_number_single_digit(self):
        toks = [t for t in scan('5') if t.type != TokenType.EOF]
        assert toks[0].type == TokenType.NUMBER
        assert toks[0].value == '5'

    def test_number_multi_digit(self):
        toks = [t for t in scan('10') if t.type != TokenType.EOF]
        assert toks[0].type == TokenType.NUMBER
        assert toks[0].value == '10'

    def test_number_zero(self):
        toks = [t for t in scan('0') if t.type != TokenType.EOF]
        assert toks[0].value == '0'


# ---------------------------------------------------------------------------
# Identificadores
# ---------------------------------------------------------------------------

class TestIdentifiers:
    def test_simple_ident(self):
        assert types('foo') == [TokenType.IDENT]
        assert values('foo') == ['foo']

    def test_ident_with_underscore(self):
        assert types('status_var') == [TokenType.IDENT]
        assert values('status_var') == ['status_var']

    def test_ident_with_digits(self):
        assert types('foo2') == [TokenType.IDENT]

    def test_ident_not_confused_with_keyword(self):
        # 'programs' não é keyword
        assert types('programs') == [TokenType.IDENT]

    def test_output_code_ident(self):
        # Códigos de saída como ONLINE, OFFLINE são IDENT
        assert types('ONLINE') == [TokenType.IDENT]
        assert types('OFFLINE') == [TokenType.IDENT]


# ---------------------------------------------------------------------------
# Comentários
# ---------------------------------------------------------------------------

class TestComments:
    def test_line_comment_ignored(self):
        assert types('// isso é um comentário\nfoo') == [TokenType.IDENT]

    def test_line_comment_at_end(self):
        assert types('foo // comentário') == [TokenType.IDENT]

    def test_block_comment_ignored(self):
        assert types('/* comentário */ foo') == [TokenType.IDENT]

    def test_block_comment_multiline(self):
        assert types('/* linha 1\nlinha 2 */ foo') == [TokenType.IDENT]

    def test_only_comment_produces_no_tokens(self):
        assert types('// tudo comentário') == []

    def test_block_comment_only(self):
        assert types('/* bloco inteiro */') == []

    def test_comment_between_tokens(self):
        result = types('exec /* comentário */ foo')
        assert result == [TokenType.KW_EXEC, TokenType.IDENT]


# ---------------------------------------------------------------------------
# Rastreamento de linha
# ---------------------------------------------------------------------------

class TestLineTracking:
    def test_single_line(self):
        toks = [t for t in scan('foo') if t.type != TokenType.EOF]
        assert toks[0].line == 1

    def test_second_line(self):
        toks = [t for t in scan('foo\nbar') if t.type != TokenType.EOF]
        assert toks[0].line == 1
        assert toks[1].line == 2

    def test_after_blank_lines(self):
        toks = [t for t in scan('\n\n\nfoo') if t.type != TokenType.EOF]
        assert toks[0].line == 4

    def test_after_line_comment(self):
        toks = [t for t in scan('// comentário\nfoo') if t.type != TokenType.EOF]
        assert toks[0].line == 2

    def test_after_block_comment_multiline(self):
        toks = [t for t in scan('/* linha1\nlinha2\n*/foo') if t.type != TokenType.EOF]
        assert toks[0].line == 3

    def test_eof_line(self):
        toks = scan('foo\nbar')
        eof = toks[-1]
        assert eof.type == TokenType.EOF
        assert eof.line == 2


# ---------------------------------------------------------------------------
# EOF
# ---------------------------------------------------------------------------

class TestEOF:
    def test_empty_source(self):
        toks = scan('')
        assert len(toks) == 1
        assert toks[0].type == TokenType.EOF

    def test_eof_always_last(self):
        toks = scan('foo bar')
        assert toks[-1].type == TokenType.EOF


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------

class TestErrors:
    def test_invalid_char(self):
        with pytest.raises(ScannerError):
            scan('#')

    def test_unclosed_string(self):
        with pytest.raises(ScannerError):
            scan('"não fechada')

    def test_string_newline(self):
        with pytest.raises(ScannerError):
            scan('"linha\nquebrada"')

    def test_unclosed_block_comment(self):
        with pytest.raises(ScannerError):
            scan('/* não fechado')

    def test_error_contains_line_number(self):
        with pytest.raises(ScannerError) as exc_info:
            scan('\n\n#')
        assert exc_info.value.line == 3


# ---------------------------------------------------------------------------
# Integração: examples/basic.gnj
# ---------------------------------------------------------------------------

class TestBasicGnj:
    BASIC_GNJ = """\
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
"""

    def test_tokenizes_without_error(self):
        toks = scan(self.BASIC_GNJ)
        assert toks[-1].type == TokenType.EOF

    def test_contains_program_keyword(self):
        assert TokenType.KW_PROGRAM in types(self.BASIC_GNJ)

    def test_contains_arrow(self):
        assert TokenType.ARROW in types(self.BASIC_GNJ)

    def test_no_invalid_rangle_from_arrow(self):
        """>> em exec deve ser ARROW, não RANGLE."""
        toks = [t for t in scan(self.BASIC_GNJ) if t.type != TokenType.EOF]
        arrow_count = sum(1 for t in toks if t.type == TokenType.ARROW)
        assert arrow_count == 2  # exec verificar_rede() >> e exec enviar(...) >>

    def test_program_name_string(self):
        toks = [t for t in scan(self.BASIC_GNJ) if t.type != TokenType.EOF]
        strings = [t.value for t in toks if t.type == TokenType.STRING]
        assert 'Sistema de Pagamento' in strings

    def test_all_keywords_present(self):
        result = types(self.BASIC_GNJ)
        for kw in [
            TokenType.KW_PROGRAM, TokenType.KW_VARS, TokenType.KW_PROCS,
            TokenType.KW_FROM, TokenType.KW_EXEC,
            TokenType.KW_CASE, TokenType.KW_PASS, TokenType.KW_WHILE,
            TokenType.KW_CODES,
        ]:
            assert kw in result, f'{kw} não encontrado nos tokens de basic.gnj'


# ---------------------------------------------------------------------------
# OBJECT_LITERAL — literais de coleção em lista de argumentos
# ---------------------------------------------------------------------------

class TestObjectLiteral:
    """Testes para o token OBJECT_LITERAL emitido dentro de listas de argumentos."""

    def _obj_tokens(self, source: str) -> list[Token]:
        return [t for t in scan(source) if t.type == TokenType.OBJECT_LITERAL]

    # --- lista simples ---

    def test_list_literal_simple(self):
        """['diamond_axe'] deve gerar um OBJECT_LITERAL."""
        src = "exec P(itens=['diamond_axe'])"
        toks = self._obj_tokens(src)
        assert len(toks) == 1
        assert toks[0].value == "['diamond_axe']"

    def test_list_literal_multiple_elements(self):
        """['diamond_axe', 'iron_axe'] gera OBJECT_LITERAL com valor completo."""
        src = "exec P(itens=['diamond_axe', 'iron_axe'])"
        toks = self._obj_tokens(src)
        assert toks[0].value == "['diamond_axe', 'iron_axe']"

    def test_list_literal_nested(self):
        """Lista aninhada [['a'], ['b']] gera um único OBJECT_LITERAL."""
        src = "exec P(x=[['a'], ['b']])"
        toks = self._obj_tokens(src)
        assert len(toks) == 1
        assert toks[0].value == "[['a'], ['b']]"

    # --- dicionário simples ---

    def test_dict_literal_simple(self):
        """{'chave': 'valor'} deve gerar um OBJECT_LITERAL."""
        src = "exec P(config={'chave': 'valor'})"
        toks = self._obj_tokens(src)
        assert len(toks) == 1
        assert toks[0].value == "{'chave': 'valor'}"

    def test_dict_literal_nested(self):
        """Dicionário com lista aninhada gera OBJECT_LITERAL correto."""
        src = "exec P(cfg={'a': [1, 2]})"
        toks = self._obj_tokens(src)
        assert toks[0].value == "{'a': [1, 2]}"

    # --- múltiplos argumentos ---

    def test_multiple_object_args(self):
        """Dois parâmetros Object geram dois OBJECT_LITERAL distintos."""
        src = "exec P(itens=['x'], cfg={'k': 'v'})"
        toks = self._obj_tokens(src)
        assert len(toks) == 2
        assert toks[0].value == "['x']"
        assert toks[1].value == "{'k': 'v'}"

    # --- Type[] NÃO deve gerar OBJECT_LITERAL ---

    def test_type_plural_not_object_literal_outside_paren(self):
        """Text[] fora de parênteses emite LBRACKET + RBRACKET, não OBJECT_LITERAL."""
        result = types("param: Text[]")
        assert TokenType.OBJECT_LITERAL not in result
        assert TokenType.LBRACKET in result
        assert TokenType.RBRACKET in result

    def test_type_plural_not_object_literal_inside_paren(self):
        """Type[] como argumento NÃO deve gerar OBJECT_LITERAL — é uma edge case
        da regra peek==']: Text[] dentro de parênteses ainda emite LBRACKET."""
        src = "exec P(type=Text[])"
        result = types(src)
        # Sem OBJECT_LITERAL: o [ seguido de ] → LBRACKET pelo peek
        assert TokenType.OBJECT_LITERAL not in result

    # --- lista vazia fora de arg list ---

    def test_empty_list_outside_paren(self):
        """[] fora de arglist (paren_depth==0) → LBRACKET + RBRACKET."""
        result = types("[]")
        assert result == [TokenType.LBRACKET, TokenType.RBRACKET]

    # --- erro: literal não fechado ---

    def test_unclosed_list_literal_raises(self):
        with pytest.raises(ScannerError):
            scan("exec P(x=['sem_fechar')")

    def test_unclosed_dict_literal_raises(self):
        with pytest.raises(ScannerError):
            scan("exec P(x={'sem_fechar')")

    # --- linha rastreada ---

    def test_line_tracking_preserved(self):
        src = "exec P(\n    itens=['x']\n)"
        toks = self._obj_tokens(src)
        assert len(toks) == 1
        assert toks[0].line == 2
