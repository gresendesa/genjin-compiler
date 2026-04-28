"""
Etapa 2:
Análise sintática/semântica
Saída: AST (Abstract Syntax Tree)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from compiler.scanner import Token, TokenType, Scanner


# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

@dataclass
class ArgNode:
    value: Any               # str | int para literal; str (nome da var) para ref
    evaluation: str          # 'literal' | 'reference'


@dataclass
class OutputCodeNode:
    name: str
    code: int


@dataclass
class ParamDeclNode:
    name: str
    type: str                # 'number' | 'text' | 'logic'
    cardinality: str         # 'singular'
    evaluation: str          # 'literal' | 'reference'


@dataclass
class ProcDeclNode:
    name: str
    library: str
    macro: str
    parameters: list[ParamDeclNode]
    output_codes: list[OutputCodeNode]


@dataclass
class VarDeclNode:
    name: str
    type: str                # 'number' | 'text' | 'logic'
    cardinality: str         # 'singular' | 'plural'
    value: Any               # None se não declarado


@dataclass
class ExecBlockNode:
    proc_name: str
    kwargs: dict[str, ArgNode]
    variable: str | None     # variável resolvida (incluindo herança)
    variable_explicit: bool  # True se >> foi declarado no fonte
    block_name: str | None   # None = usa nome do proc
    cases: list[CaseNode]
    loop_while: list[str]
    pass_codes: list[str]


@dataclass
class CaseNode:
    output_code: str
    block: ExecBlockNode


@dataclass
class ProgramNode:
    name: str
    variables: list[VarDeclNode]
    procedures: list[ProcDeclNode]
    block: ExecBlockNode


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------

class ParseError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"Linha {line}: {message}")
        self.line = line


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    TokenType.TYPE_NUMBER: 'number',
    TokenType.TYPE_TEXT:   'text',
    TokenType.TYPE_LOGIC:  'logic',
}


class Parser:
    """Recursive-descent parser para a DSL Genjin (.gnj)."""

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    # ------------------------------------------------------------------
    # Primitivas de navegação
    # ------------------------------------------------------------------

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _expect(self, ttype: TokenType, msg: str | None = None) -> Token:
        tok = self._peek()
        if tok.type != ttype:
            desc = msg or f"esperado {ttype.name!r}"
            raise ParseError(desc, tok.line)
        return self._advance()

    # ------------------------------------------------------------------
    # Ponto de entrada
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        node = self._parse_program()
        self._expect(TokenType.EOF, "caractere inesperado após fim do programa")
        return node

    # ------------------------------------------------------------------
    # program
    # ------------------------------------------------------------------

    def _parse_program(self) -> ProgramNode:
        self._expect(TokenType.KW_PROGRAM, "esperado 'program'")
        name_tok = self._expect(TokenType.STRING, "esperado nome do programa como string")
        variables = self._parse_vars()
        procedures = self._parse_procs()
        block = self._parse_exec(declared_vars={v.name for v in variables},
                                 declared_procs={p.name: p for p in procedures},
                                 inherited_var=None)
        return ProgramNode(name=name_tok.value,
                           variables=variables,
                           procedures=procedures,
                           block=block)

    # ------------------------------------------------------------------
    # vars
    # ------------------------------------------------------------------

    def _parse_vars(self) -> list[VarDeclNode]:
        self._expect(TokenType.KW_VARS, "esperado 'vars'")
        self._expect(TokenType.LBRACE, "esperado '{' após 'vars'")
        variables: list[VarDeclNode] = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            variables.append(self._parse_var_decl())
        self._expect(TokenType.RBRACE, "esperado '}' para fechar 'vars'")
        return variables

    def _parse_var_decl(self) -> VarDeclNode:
        name_tok = self._expect(TokenType.IDENT, "esperado nome de variável")
        self._expect(TokenType.COLON, "esperado ':' após nome de variável")
        type_tok = self._peek()
        if type_tok.type not in _TYPE_MAP:
            raise ParseError(f"tipo desconhecido '{type_tok.value}'", type_tok.line)
        self._advance()
        var_type = _TYPE_MAP[type_tok.type]

        cardinality = 'singular'
        if self._check(TokenType.LBRACKET):
            self._advance()
            self._expect(TokenType.RBRACKET, "esperado ']' após '['")
            cardinality = 'plural'

        value = None
        if self._check(TokenType.ASSIGN):
            self._advance()
            val_tok = self._peek()
            if val_tok.type == TokenType.STRING:
                value = val_tok.value
                self._advance()
            elif val_tok.type == TokenType.NUMBER:
                value = int(val_tok.value)
                self._advance()
            else:
                raise ParseError(f"valor inicial inválido '{val_tok.value}'", val_tok.line)

        return VarDeclNode(name=name_tok.value,
                           type=var_type,
                           cardinality=cardinality,
                           value=value)

    # ------------------------------------------------------------------
    # procs
    # ------------------------------------------------------------------

    def _parse_procs(self) -> list[ProcDeclNode]:
        self._expect(TokenType.KW_PROCS, "esperado 'procs'")
        self._expect(TokenType.LBRACE, "esperado '{' após 'procs'")
        procedures: list[ProcDeclNode] = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            procedures.append(self._parse_proc_decl())
        self._expect(TokenType.RBRACE, "esperado '}' para fechar 'procs'")
        return procedures

    def _parse_proc_decl(self) -> ProcDeclNode:
        self._expect(TokenType.KW_PROC, "esperado 'proc'")
        name_tok = self._expect(TokenType.IDENT, "esperado nome do proc")
        self._expect(TokenType.LPAREN, "esperado '(' após nome do proc")
        params = self._parse_param_list()
        self._expect(TokenType.RPAREN, "esperado ')' após parâmetros")
        self._expect(TokenType.KW_FROM, "esperado 'from'")
        from_tok = self._expect(TokenType.STRING, "esperado caminho em 'from'")
        library, macro = self._resolve_from(from_tok.value, from_tok.line)
        self._expect(TokenType.LBRACE, "esperado '{' no corpo do proc")
        self._expect(TokenType.KW_CODES, "esperado 'codes'")
        codes = self._parse_codes()
        self._expect(TokenType.RBRACE, "esperado '}' para fechar proc")
        return ProcDeclNode(name=name_tok.value,
                            library=library,
                            macro=macro,
                            parameters=params,
                            output_codes=codes)

    def _parse_param_list(self) -> list[ParamDeclNode]:
        params: list[ParamDeclNode] = []
        while not self._check(TokenType.RPAREN, TokenType.EOF):
            if params:
                self._expect(TokenType.COMMA, "esperado ',' entre parâmetros")
            params.append(self._parse_param_decl())
        return params

    def _parse_param_decl(self) -> ParamDeclNode:
        name_tok = self._expect(TokenType.IDENT, "esperado nome do parâmetro")
        self._expect(TokenType.COLON, "esperado ':' após nome do parâmetro")
        evaluation = 'literal'
        if self._check(TokenType.AMPERSAND):
            self._advance()
            evaluation = 'reference'
        type_tok = self._peek()
        if type_tok.type not in _TYPE_MAP:
            raise ParseError(f"tipo desconhecido '{type_tok.value}'", type_tok.line)
        self._advance()
        return ParamDeclNode(name=name_tok.value,
                             type=_TYPE_MAP[type_tok.type],
                             cardinality='singular',
                             evaluation=evaluation)

    def _parse_codes(self) -> list[OutputCodeNode]:
        codes: list[OutputCodeNode] = []
        while self._check(TokenType.IDENT):
            name_tok = self._advance()
            self._expect(TokenType.LANGLE, "esperado '<' após nome do código")
            num_tok = self._expect(TokenType.NUMBER, "esperado número do código")
            self._expect(TokenType.RANGLE, "esperado '>' após número do código")
            codes.append(OutputCodeNode(name=name_tok.value, code=int(num_tok.value)))
            if self._check(TokenType.COMMA):
                self._advance()
        return codes

    @staticmethod
    def _resolve_from(path: str, line: int) -> tuple[str, str]:
        dot = path.rfind('.')
        if dot < 0:
            raise ParseError(f"'from' deve ter pelo menos um ponto: '{path}'", line)
        return path[:dot], path[dot + 1:]

    # ------------------------------------------------------------------
    # exec
    # ------------------------------------------------------------------

    def _parse_exec(self,
                    declared_vars: set[str],
                    declared_procs: dict[str, ProcDeclNode],
                    inherited_var: str | None) -> ExecBlockNode:
        exec_tok = self._expect(TokenType.KW_EXEC, "esperado 'exec'")
        proc_name_tok = self._expect(TokenType.IDENT, "esperado nome do proc em 'exec'")
        proc_name = proc_name_tok.value

        # Validação semântica: proc deve estar declarado
        if proc_name not in declared_procs:
            raise ParseError(
                f"proc '{proc_name}' não declarado em 'procs'",
                proc_name_tok.line,
            )

        proc_decl = declared_procs[proc_name]
        self._expect(TokenType.LPAREN, "esperado '(' após nome do proc")
        kwargs = self._parse_kwargs(proc_decl, declared_vars, exec_tok.line)
        self._expect(TokenType.RPAREN, "esperado ')' após argumentos")

        # >> variavel (opcional — herança)
        variable: str | None = None
        variable_explicit = False
        if self._check(TokenType.ARROW):
            self._advance()
            var_tok = self._expect(TokenType.IDENT, "esperado nome de variável após '>'")
            # Validação semântica: variável deve estar declarada
            if var_tok.value not in declared_vars:
                raise ParseError(
                    f"variável '{var_tok.value}' não declarada em 'vars'",
                    var_tok.line,
                )
            variable = var_tok.value
            variable_explicit = True
        else:
            variable = inherited_var

        # as "nome" (opcional)
        block_name: str | None = None
        if self._check(TokenType.KW_AS):
            self._advance()
            name_tok = self._expect(TokenType.STRING, "esperado string após 'as'")
            block_name = name_tok.value

        self._expect(TokenType.LBRACE, "esperado '{' no corpo do exec")
        cases, pass_codes = self._parse_exec_body(
            proc_decl, declared_vars, declared_procs, variable
        )
        self._expect(TokenType.RBRACE, "esperado '}' para fechar exec")

        # while(...) aparece DEPOIS do }, não dentro do corpo
        loop_while: list[str] = []
        if self._check(TokenType.KW_WHILE):
            valid_codes = {oc.name for oc in proc_decl.output_codes}
            loop_while = self._parse_while(valid_codes)

        # Validação semântica: todos os códigos DO PROC ATUAL não tratados
        # devem aparecer em pass (pass pode conter também códigos borbulhados de filhos)
        valid_codes = {oc.name for oc in proc_decl.output_codes}
        case_while_handled = {c.output_code for c in cases} | set(loop_while)
        must_pass = valid_codes - case_while_handled
        missing = must_pass - set(pass_codes)
        if missing:
            raise ParseError(
                f"código '{sorted(missing)[0]}' não tratado e sem 'pass'",
                self._peek().line,
            )

        return ExecBlockNode(
            proc_name=proc_name,
            kwargs=kwargs,
            variable=variable,
            variable_explicit=variable_explicit,
            block_name=block_name,
            cases=cases,
            loop_while=loop_while,
            pass_codes=pass_codes,
        )

    def _parse_kwargs(self,
                      proc_decl: ProcDeclNode,
                      declared_vars: set[str],
                      exec_line: int) -> dict[str, ArgNode]:
        # Índice dos parâmetros por nome
        param_index = {p.name: p for p in proc_decl.parameters}
        kwargs: dict[str, ArgNode] = {}
        while not self._check(TokenType.RPAREN, TokenType.EOF):
            if kwargs:
                self._expect(TokenType.COMMA, "esperado ',' entre argumentos")
            name_tok = self._expect(TokenType.IDENT, "esperado nome do argumento")
            self._expect(TokenType.ASSIGN, "esperado '=' após nome do argumento")

            param = param_index.get(name_tok.value)
            if param is None:
                raise ParseError(
                    f"parâmetro '{name_tok.value}' não existe em '{proc_decl.name}'",
                    name_tok.line,
                )

            # & indica referência
            if self._check(TokenType.AMPERSAND):
                self._advance()
                var_tok = self._expect(TokenType.IDENT, "esperado nome de variável após '&'")
                if var_tok.value not in declared_vars:
                    raise ParseError(
                        f"variável '{var_tok.value}' não declarada em 'vars'",
                        var_tok.line,
                    )
                kwargs[name_tok.value] = ArgNode(value=var_tok.value, evaluation='reference')
            else:
                # Literal
                if param.evaluation == 'reference':
                    raise ParseError(
                        f"parâmetro '{param.name}' exige argumento por referência (=&var)",
                        name_tok.line,
                    )
                val_tok = self._peek()
                if val_tok.type == TokenType.STRING:
                    self._advance()
                    kwargs[name_tok.value] = ArgNode(value=val_tok.value, evaluation='literal')
                elif val_tok.type == TokenType.NUMBER:
                    self._advance()
                    kwargs[name_tok.value] = ArgNode(value=int(val_tok.value), evaluation='literal')
                else:
                    raise ParseError(f"valor inválido para argumento '{name_tok.value}'", val_tok.line)

        return kwargs

    def _parse_exec_body(
        self,
        proc_decl: ProcDeclNode,
        declared_vars: set[str],
        declared_procs: dict[str, ProcDeclNode],
        inherited_var: str | None,
    ) -> tuple[list[CaseNode], list[str]]:
        """Parseia o interior de { } de um exec. Retorna (cases, pass_codes).
        O while(...) fica FORA do corpo, após o }, e é tratado em _parse_exec.
        """
        valid_codes = {oc.name for oc in proc_decl.output_codes}
        cases: list[CaseNode] = []
        pass_codes: list[str] = []

        while not self._check(TokenType.RBRACE, TokenType.EOF):
            if self._check(TokenType.KW_CASE):
                case_node = self._parse_case(valid_codes, declared_vars,
                                             declared_procs, inherited_var,
                                             proc_decl)
                cases.append(case_node)
            elif self._check(TokenType.KW_PASS):
                codes = self._parse_pass(valid_codes)
                pass_codes.extend(codes)
            else:
                tok = self._peek()
                raise ParseError(
                    f"token inesperado '{tok.value}' no corpo do exec",
                    tok.line,
                )

        return cases, pass_codes

    def _parse_case(self,
                    valid_codes: set[str],
                    declared_vars: set[str],
                    declared_procs: dict[str, ProcDeclNode],
                    inherited_var: str | None,
                    proc_decl: ProcDeclNode) -> CaseNode:
        self._expect(TokenType.KW_CASE, "esperado 'case'")
        code_tok = self._expect(TokenType.IDENT, "esperado código após 'case'")
        if code_tok.value not in valid_codes:
            raise ParseError(
                f"código '{code_tok.value}' não declarado no proc '{proc_decl.name}'",
                code_tok.line,
            )
        self._expect(TokenType.COLON, "esperado ':' após código do case")
        child_block = self._parse_exec(declared_vars, declared_procs, inherited_var)
        return CaseNode(output_code=code_tok.value, block=child_block)

    def _parse_while(self, valid_codes: set[str]) -> list[str]:
        self._expect(TokenType.KW_WHILE, "esperado 'while'")
        self._expect(TokenType.LPAREN, "esperado '(' após 'while'")
        codes: list[str] = []
        while not self._check(TokenType.RPAREN, TokenType.EOF):
            if codes:
                self._expect(TokenType.COMMA, "esperado ',' entre códigos no while")
            code_tok = self._expect(TokenType.IDENT, "esperado código no while")
            if code_tok.value not in valid_codes:
                raise ParseError(
                    f"código '{code_tok.value}' em 'while' não declarado no proc",
                    code_tok.line,
                )
            codes.append(code_tok.value)
        self._expect(TokenType.RPAREN, "esperado ')' após códigos do while")
        return codes

    def _parse_pass(self, valid_codes: set[str]) -> list[str]:
        self._expect(TokenType.KW_PASS, "esperado 'pass'")
        codes: list[str] = []
        while self._check(TokenType.IDENT):
            code_tok = self._advance()
            # Pass aceita qualquer IDENT: podem ser códigos do proc atual
            # ou códigos borbulhados de procs filhos
            codes.append(code_tok.value)
            if self._check(TokenType.COMMA):
                self._advance()
        return codes


# ---------------------------------------------------------------------------
# Função de conveniência
# ---------------------------------------------------------------------------

def parse(source: str) -> ProgramNode:
    """Tokeniza e parseia um programa .gnj, retornando a AST raiz."""
    tokens = Scanner(source).tokenize()
    return Parser(tokens).parse()
