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

    def test_all_keywords_sequence(self):
        src = 'program vars procs from exec case pass while as codes'
        expected = [
            TokenType.KW_PROGRAM, TokenType.KW_VARS, TokenType.KW_PROCS,
            TokenType.KW_FROM, TokenType.KW_EXEC,
            TokenType.KW_CASE, TokenType.KW_PASS, TokenType.KW_WHILE,
            TokenType.KW_AS, TokenType.KW_CODES,
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
            scan('@')

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
            scan('\n\n@')
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
