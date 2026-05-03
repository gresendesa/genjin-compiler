'''
Etapa 1:
Análise lexográfica
Saída: lista de tokens
'''

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Keywords
    KW_PROGRAM  = auto()
    KW_VARS     = auto()
    KW_PROCS    = auto()
    KW_PROC     = auto()   # deprecado: 'proc' não é mais keyword ativa
    KW_FROM     = auto()
    KW_EXEC     = auto()
    KW_CASE     = auto()
    KW_PASS     = auto()
    KW_WHILE    = auto()
    KW_AS       = auto()
    KW_CODES    = auto()
    KW_WHEN     = auto()
    # Tipos primitivos
    TYPE_NUMBER = auto()
    TYPE_TEXT   = auto()
    TYPE_LOGIC  = auto()
    TYPE_OBJECT = auto()
    # Símbolos
    LBRACE      = auto()   # {
    RBRACE      = auto()   # }
    LPAREN      = auto()   # (
    RPAREN      = auto()   # )
    LANGLE      = auto()   # <
    RANGLE      = auto()   # >
    LBRACKET    = auto()   # [
    RBRACKET    = auto()   # ]
    COLON       = auto()   # :
    COMMA       = auto()   # ,
    AMPERSAND   = auto()   # &
    ASSIGN      = auto()   # =
    ARROW       = auto()   # >>
    AT          = auto()   # @
    # Literais e identificadores
    STRING      = auto()   # "valor"
    NUMBER      = auto()   # inteiro
    IDENT       = auto()   # identificador
    # Especial
    EOF         = auto()


_KEYWORDS: dict[str, TokenType] = {
    'program': TokenType.KW_PROGRAM,
    'vars':    TokenType.KW_VARS,
    'procs':   TokenType.KW_PROCS,
    # 'proc' foi removido das keywords; agora é reconhecido como IDENT
    'from':    TokenType.KW_FROM,
    'exec':    TokenType.KW_EXEC,
    'case':    TokenType.KW_CASE,
    'pass':    TokenType.KW_PASS,
    'while':   TokenType.KW_WHILE,
    'as':      TokenType.KW_AS,
    'codes':   TokenType.KW_CODES,
    'when':    TokenType.KW_WHEN,
    'Number':  TokenType.TYPE_NUMBER,
    'Text':    TokenType.TYPE_TEXT,
    'Logic':   TokenType.TYPE_LOGIC,
    'Object':  TokenType.TYPE_OBJECT,
}


@dataclass
class Token:
    type: TokenType
    value: str
    line: int

    def __repr__(self) -> str:
        return f'Token({self.type.name}, {self.value!r}, line={self.line})'


class ScannerError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f'[Linha {line}] {message}')
        self.line = line


class Scanner:
    def __init__(self, source: str):
        self._src = source
        self._pos = 0
        self._line = 1

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            tok = self._next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        idx = self._pos + offset
        return self._src[idx] if idx < len(self._src) else ''

    def _advance(self) -> str:
        ch = self._src[self._pos]
        self._pos += 1
        if ch == '\n':
            self._line += 1
        return ch

    def _skip_whitespace(self) -> None:
        while self._pos < len(self._src) and self._peek().isspace():
            self._advance()

    def _skip_line_comment(self) -> None:
        # Já consumiu '//'
        while self._pos < len(self._src) and self._peek() != '\n':
            self._advance()

    def _skip_block_comment(self) -> None:
        # Já consumiu '/*'
        start_line = self._line
        while self._pos < len(self._src):
            if self._peek() == '*' and self._peek(1) == '/':
                self._advance()  # *
                self._advance()  # /
                return
            self._advance()
        raise ScannerError("Comentário de bloco não fechado", start_line)

    def _read_string(self) -> str:
        # Já consumiu '"'
        start_line = self._line
        result: list[str] = []
        while self._pos < len(self._src):
            ch = self._peek()
            if ch == '"':
                self._advance()
                return ''.join(result)
            if ch == '\n':
                raise ScannerError("String não fechada antes do fim da linha", start_line)
            result.append(self._advance())
        raise ScannerError("String não fechada antes do fim do arquivo", start_line)

    def _read_number(self, first: str) -> str:
        digits = [first]
        while self._pos < len(self._src) and self._peek().isdigit():
            digits.append(self._advance())
        return ''.join(digits)

    def _read_ident(self, first: str) -> str:
        chars = [first]
        while self._pos < len(self._src) and (self._peek().isalnum() or self._peek() == '_'):
            chars.append(self._advance())
        return ''.join(chars)

    # ------------------------------------------------------------------
    # Motor principal
    # ------------------------------------------------------------------

    def _next_token(self) -> Token:
        while True:
            self._skip_whitespace()

            if self._pos >= len(self._src):
                return Token(TokenType.EOF, '', self._line)

            line = self._line
            ch = self._advance()

            # Comentários
            if ch == '/' and self._peek() == '/':
                self._advance()
                self._skip_line_comment()
                continue
            if ch == '/' and self._peek() == '*':
                self._advance()
                self._skip_block_comment()
                continue

            # Símbolos de um caractere (e >> como caso especial)
            if ch == '>':
                if self._peek() == '>':
                    self._advance()
                    return Token(TokenType.ARROW, '>>', line)
                return Token(TokenType.RANGLE, '>', line)

            _SINGLE: dict[str, TokenType] = {
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '<': TokenType.LANGLE,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
                ':': TokenType.COLON,
                ',': TokenType.COMMA,
                '&': TokenType.AMPERSAND,
                '=': TokenType.ASSIGN,
                '@': TokenType.AT,
            }
            if ch in _SINGLE:
                return Token(_SINGLE[ch], ch, line)

            # String literal
            if ch == '"':
                value = self._read_string()
                return Token(TokenType.STRING, value, line)

            # Número
            if ch.isdigit():
                value = self._read_number(ch)
                return Token(TokenType.NUMBER, value, line)

            # Identificador ou keyword
            if ch.isalpha() or ch == '_':
                value = self._read_ident(ch)
                tok_type = _KEYWORDS.get(value, TokenType.IDENT)
                return Token(tok_type, value, line)

            raise ScannerError(f"Caractere não reconhecido: {ch!r}", line)


if __name__ == '__main__':
    import sys
    from compiler.ast_io import tokens_to_json

    if len(sys.argv) > 2:
        print('Uso: python -m compiler.scanner [arquivo]', file=sys.stderr)
        sys.exit(2)

    if len(sys.argv) == 2:
        try:
            source = open(sys.argv[1], encoding='utf-8').read()
        except OSError as exc:
            print(f'Erro ao ler arquivo: {exc}', file=sys.stderr)
            sys.exit(2)
    else:
        source = sys.stdin.read()

    try:
        tokens = Scanner(source).tokenize()
    except ScannerError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(tokens_to_json(tokens))
