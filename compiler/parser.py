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
    raw: bool = False        # True para Object literal (valor emitido sem aspas no Jinja2)


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
class ProcBlockNode:
    name: str
    parameters: list[ParamDeclNode]
    block: ExecBlockNode | InlineSeqNode  # corpo do proc-bloco
    inferred_codes: list[str]             # inferido dos pass_codes do bloco raiz


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
    block: ExecBlockNode | InlineSeqNode  # InlineSeqNode possível antes do desugar


@dataclass
class InlineAtomNode:
    """Átomo da notação inline @proc() [>> var] [while(W)] [when(CODE)]."""
    proc_name: str
    kwargs: dict[str, ArgNode]
    variable: str | None        # de >>
    variable_explicit: bool
    while_code: str | None      # de while(CODE)
    when_code: str | None       # de when(CODE) — None no átomo terminal


@dataclass
class InlineSeqNode:
    """Sequência inline: átomos encadeados + terminal.

    chained: todos os átomos que têm when_code (não-terminais)
    terminal: último átomo (sem when) ou ExecBlockNode canônico
    """
    chained: list[InlineAtomNode]
    terminal: InlineAtomNode | ExecBlockNode


@dataclass
class ProgramNode:
    name: str
    variables: list[VarDeclNode]
    procedures: list[ProcDeclNode | ProcBlockNode]
    block: ExecBlockNode | InlineSeqNode  # InlineSeqNode possível antes do desugar


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
    TokenType.TYPE_OBJECT: 'object',
}


class Parser:
    """Recursive-descent parser para a DSL Genjin (.gnj)."""

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0
        self._pb_param_names: frozenset[str] = frozenset()

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

    @staticmethod
    def _output_code_names(proc: ProcDeclNode | ProcBlockNode) -> set[str]:
        """Retorna o conjunto de nomes de códigos de saída de um proc (normal ou bloco)."""
        if isinstance(proc, ProcBlockNode):
            return set(proc.inferred_codes)
        return {oc.name for oc in proc.output_codes}

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

        _BLOCK_TOKENS = {TokenType.KW_VARS, TokenType.KW_PROCS,
                         TokenType.KW_EXEC, TokenType.AT}

        variables: list[VarDeclNode] | None = None
        procs_pos: int | None = None
        exec_pos: int | None = None  # posição do token 'exec' ou '@' na lista de tokens

        # Primeiro passo: coletar vars completamente; skip procs e exec/inline (posições guardadas)
        while self._check(*_BLOCK_TOKENS):
            tok = self._peek()
            if tok.type == TokenType.KW_VARS:
                if variables is not None:
                    raise ParseError("bloco 'vars' declarado mais de uma vez", tok.line)
                variables = self._parse_vars()
            elif tok.type == TokenType.KW_PROCS:
                if procs_pos is not None:
                    raise ParseError("bloco 'procs' declarado mais de uma vez", tok.line)
                procs_pos = self._pos
                self._skip_kw_brace_block()
            elif tok.type in (TokenType.KW_EXEC, TokenType.AT):
                if exec_pos is not None:
                    raise ParseError("bloco 'exec' raiz declarado mais de uma vez", tok.line)
                exec_pos = self._pos
                if tok.type == TokenType.KW_EXEC:
                    self._skip_exec_block()
                else:
                    self._skip_inline_seq()

        if variables is None:
            raise ParseError("bloco 'vars' ausente", self._peek().line)
        if procs_pos is None:
            raise ParseError("bloco 'procs' ausente", self._peek().line)
        if exec_pos is None:
            raise ParseError("bloco 'exec' raiz ausente", self._peek().line)

        end_pos = self._pos

        # Segundo passo: parsear procs com declared_vars disponível
        self._pos = procs_pos
        procedures = self._parse_procs(declared_vars={v.name for v in variables})

        # Terceiro passo: parsear exec/inline com vars e procs completos
        self._pos = exec_pos
        declared_procs = {p.name: p for p in procedures}
        block = self._parse_exec_or_inline(
            declared_vars={v.name for v in variables},
            declared_procs=declared_procs,
            inherited_var=None,
        )
        self._pos = end_pos

        return ProgramNode(name=name_tok.value,
                           variables=variables,
                           procedures=procedures,
                           block=block)

    def _skip_brace_block(self) -> None:
        """Avança pelo bloco { ... } sem parsear semanticamente. Consome o { inicial."""
        self._expect(TokenType.LBRACE, "esperado '{'")
        depth = 1
        while depth > 0 and not self._check(TokenType.EOF):
            tok = self._advance()
            if tok.type == TokenType.LBRACE:
                depth += 1
            elif tok.type == TokenType.RBRACE:
                depth -= 1

    def _skip_kw_brace_block(self) -> None:
        """Avança pelo bloco KEYWORD { ... } sem parsear semanticamente."""
        self._advance()  # keyword (e.g. KW_PROCS)
        self._skip_brace_block()

    def _skip_exec_block(self) -> None:
        """Avança o cursor por um bloco exec (e while opcional) sem parsear semanticamente."""
        # Pula até encontrar '{' de abertura (ignorando '()' dos args)
        paren_depth = 0
        while not self._check(TokenType.EOF):
            tok = self._advance()
            if tok.type == TokenType.LPAREN:
                paren_depth += 1
            elif tok.type == TokenType.RPAREN:
                paren_depth -= 1
            elif tok.type == TokenType.LBRACE and paren_depth == 0:
                break
        # Conta chaves até fechar o bloco raiz
        brace_depth = 1
        while brace_depth > 0 and not self._check(TokenType.EOF):
            tok = self._advance()
            if tok.type == TokenType.LBRACE:
                brace_depth += 1
            elif tok.type == TokenType.RBRACE:
                brace_depth -= 1
        # Pula while(...) opcional
        if self._check(TokenType.KW_WHILE):
            self._advance()  # while
            self._advance()  # (
            while not self._check(TokenType.RPAREN, TokenType.EOF):
                self._advance()
            if self._check(TokenType.RPAREN):
                self._advance()  # )

    def _skip_inline_seq(self) -> None:
        """Avança o cursor por uma sequência de átomos inline (@proc()...) sem parsear."""
        while self._check(TokenType.AT):
            self._advance()  # @
            self._advance()  # IDENT (proc name)
            self._advance()  # (
            paren_depth = 1
            while paren_depth > 0 and not self._check(TokenType.EOF):
                tok = self._advance()
                if tok.type == TokenType.LPAREN:
                    paren_depth += 1
                elif tok.type == TokenType.RPAREN:
                    paren_depth -= 1
            # Opcional: >> IDENT
            if self._check(TokenType.ARROW):
                self._advance()  # >>
                self._advance()  # IDENT
            # Opcional: while(IDENT)
            if self._check(TokenType.KW_WHILE):
                self._advance()  # while
                self._advance()  # (
                self._advance()  # IDENT
                self._advance()  # )
            # Opcional: when(IDENT)
            if self._check(TokenType.KW_WHEN):
                self._advance()  # when
                self._advance()  # (
                self._advance()  # IDENT
                self._advance()  # )
        # Terminal canônico exec { } (opcional)
        if self._check(TokenType.KW_EXEC):
            self._skip_exec_block()

    # ------------------------------------------------------------------
    # exec ou inline (dispatcher)
    # ------------------------------------------------------------------

    def _parse_exec_or_inline(self,
                               declared_vars: set[str],
                               declared_procs: dict[str, ProcDeclNode | ProcBlockNode],
                               inherited_var: str | None) -> ExecBlockNode | InlineSeqNode:
        if self._check(TokenType.AT):
            return self._parse_inline_seq(declared_vars, declared_procs, inherited_var)
        return self._parse_exec(declared_vars, declared_procs, inherited_var)

    def _parse_inline_seq(self,
                          declared_vars: set[str],
                          declared_procs: dict[str, ProcDeclNode | ProcBlockNode],
                          inherited_var: str | None) -> InlineSeqNode:
        """Parseia uma sequência inline: (átomo with when)* átomo-terminal|exec."""
        chained: list[InlineAtomNode] = []

        while self._check(TokenType.AT):
            atom = self._parse_inline_atom(declared_vars, declared_procs)
            if atom.when_code is not None:
                chained.append(atom)
            else:
                # Átomo terminal (sem when)
                if len(chained) == 0 and atom.when_code is None:
                    # Tipo 1 — sequência de um único átomo simples
                    return InlineSeqNode(chained=[], terminal=atom)
                return InlineSeqNode(chained=chained, terminal=atom)

        # Nenhum @ encontrado: verificar se há exec canônico como terminal
        if self._check(TokenType.KW_EXEC):
            if not chained:
                raise ParseError(
                    "sequência inline vazia: esperado '@' ou 'exec'",
                    self._peek().line,
                )
            terminal = self._parse_exec(declared_vars, declared_procs, inherited_var)
            return InlineSeqNode(chained=chained, terminal=terminal)

        tok = self._peek()
        raise ParseError(
            f"sequência inline incompleta: esperado '@' ou 'exec', encontrado '{tok.value}'",
            tok.line,
        )

    def _parse_inline_atom(self,
                           declared_vars: set[str],
                           declared_procs: dict[str, ProcDeclNode | ProcBlockNode]) -> InlineAtomNode:
        """Parseia um átomo inline: @proc(args) [>> var] [while(CODE)] [when(CODE)]."""
        at_tok = self._expect(TokenType.AT, "esperado '@'")
        proc_name_tok = self._expect(TokenType.IDENT, "esperado nome do proc após '@'")
        proc_name = proc_name_tok.value

        if proc_name not in declared_procs:
            raise ParseError(
                f"proc '{proc_name}' não declarado em 'procs'",
                proc_name_tok.line,
            )
        proc_decl = declared_procs[proc_name]
        valid_codes = self._output_code_names(proc_decl)

        self._expect(TokenType.LPAREN, "esperado '(' após nome do proc")
        kwargs = self._parse_kwargs(proc_decl, declared_vars, at_tok.line)
        self._expect(TokenType.RPAREN, "esperado ')' após argumentos")

        # Opcional: >> var
        variable: str | None = None
        variable_explicit = False
        if self._check(TokenType.ARROW):
            self._advance()
            var_tok = self._expect(TokenType.IDENT, "esperado nome de variável após '>>'")
            if var_tok.value not in declared_vars:
                raise ParseError(
                    f"variável '{var_tok.value}' não declarada em 'vars'",
                    var_tok.line,
                )
            variable = var_tok.value
            variable_explicit = True

        # Opcional: while(CODE)
        while_code: str | None = None
        if self._check(TokenType.KW_WHILE):
            self._advance()  # while
            self._expect(TokenType.LPAREN, "esperado '(' após 'while'")
            code_tok = self._expect(TokenType.IDENT, "esperado código no while")
            if code_tok.value not in valid_codes:
                raise ParseError(
                    f"código '{code_tok.value}' em 'while' não declarado no proc '{proc_name}'",
                    code_tok.line,
                )
            self._expect(TokenType.RPAREN, "esperado ')' após código do while")
            while_code = code_tok.value

        # Opcional: when(CODE) — indica átomo encadeado
        when_code: str | None = None
        if self._check(TokenType.KW_WHEN):
            self._advance()  # when
            self._expect(TokenType.LPAREN, "esperado '(' após 'when'")
            code_tok = self._expect(TokenType.IDENT, "esperado código no when")
            if code_tok.value not in valid_codes:
                raise ParseError(
                    f"código '{code_tok.value}' em 'when' não declarado no proc '{proc_name}'",
                    code_tok.line,
                )
            self._expect(TokenType.RPAREN, "esperado ')' após código do when")
            when_code = code_tok.value

        return InlineAtomNode(
            proc_name=proc_name,
            kwargs=kwargs,
            variable=variable,
            variable_explicit=variable_explicit,
            while_code=while_code,
            when_code=when_code,
        )

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
        if var_type == 'object':
            raise ParseError(
                "tipo 'Object' não é permitido em 'vars'; use apenas em parâmetros de procedimentos",
                type_tok.line,
            )

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

    def _parse_procs(self, declared_vars: set[str] = frozenset()) -> list[ProcDeclNode | ProcBlockNode]:
        self._expect(TokenType.KW_PROCS, "esperado 'procs'")
        self._expect(TokenType.LBRACE, "esperado '{' após 'procs'")

        # Passo 1: coletar ProcDeclNode completos + stubs de ProcBlockNode
        ordered: list[ProcDeclNode | tuple] = []
        stubs: list[tuple[str, list[ParamDeclNode], int]] = []
        proc_decl_nodes: list[ProcDeclNode] = []

        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._peek()
            if tok.type == TokenType.IDENT and tok.value == 'proc':
                raise ParseError(
                    "keyword 'proc' não é mais necessária; escreva diretamente o nome do procedimento",
                    tok.line,
                )
            name_tok = self._expect(TokenType.IDENT, "esperado nome do proc ou proc-bloco")
            self._expect(TokenType.LPAREN, "esperado '(' após nome")
            params = self._parse_param_list()
            self._expect(TokenType.RPAREN, "esperado ')' após parâmetros")
            if self._check(TokenType.KW_FROM):
                # Proc normal
                pd = self._parse_proc_decl_tail(name_tok.value, params)
                proc_decl_nodes.append(pd)
                ordered.append(pd)
            elif self._check(TokenType.LBRACE):
                # Proc-bloco: validar params e registrar stub
                brace_tok = self._peek()
                for p in params:
                    if p.cardinality == 'plural':
                        raise ParseError(
                            f"parâmetro '{p.name}': cardinalidade plural ('[]') não é permitida em proc-blocos",
                            brace_tok.line,
                        )
                body_pos = self._pos
                self._skip_brace_block()
                stub = (name_tok.value, params, body_pos)
                stubs.append(stub)
                ordered.append(stub)
            else:
                err_tok = self._peek()
                raise ParseError(
                    f"esperado 'from' (proc normal) ou '{{' (proc-bloco) após parâmetros de '{name_tok.value}'",
                    err_tok.line,
                )

        self._expect(TokenType.RBRACE, "esperado '}' para fechar 'procs'")
        end_pos = self._pos

        # Montar declared_procs_map com todos os ProcDeclNode
        # e placeholders para ProcBlockNode (suporte a forward references)
        declared_procs_map: dict[str, ProcDeclNode | ProcBlockNode] = {}
        for pd in proc_decl_nodes:
            declared_procs_map[pd.name] = pd
        for stub_name, stub_params, _body_pos in stubs:
            declared_procs_map[stub_name] = ProcBlockNode(
                name=stub_name, parameters=stub_params, block=None, inferred_codes=[]
            )

        # Passo 2: parsear corpos dos proc-blocos com declared_procs completo
        proc_block_nodes: dict[str, ProcBlockNode] = {}
        for stub_name, stub_params, stub_body_pos in stubs:
            self._pos = stub_body_pos
            pb = self._parse_proc_block_body(
                stub_name, stub_params, declared_vars, declared_procs_map
            )
            declared_procs_map[stub_name] = pb
            proc_block_nodes[stub_name] = pb

        self._pos = end_pos

        # Reconstruir lista na ordem original de declaração
        result: list[ProcDeclNode | ProcBlockNode] = []
        for entry in ordered:
            if isinstance(entry, ProcDeclNode):
                result.append(entry)
            else:
                entry_name, _, _ = entry
                result.append(proc_block_nodes[entry_name])
        return result

    def _parse_proc_decl(self) -> ProcDeclNode:
        tok = self._peek()
        if tok.type == TokenType.IDENT and tok.value == 'proc':
            raise ParseError(
                "keyword 'proc' não é mais necessária; escreva diretamente o nome do procedimento",
                tok.line,
            )
        name_tok = self._expect(TokenType.IDENT, "esperado nome do proc")
        self._expect(TokenType.LPAREN, "esperado '(' após nome do proc")
        params = self._parse_param_list()
        self._expect(TokenType.RPAREN, "esperado ')' após parâmetros")
        return self._parse_proc_decl_tail(name_tok.value, params)

    def _parse_proc_decl_tail(self, name: str, params: list[ParamDeclNode]) -> ProcDeclNode:
        """Parseia a cauda de um proc normal (from ... { codes ... }) após nome e params."""
        self._expect(TokenType.KW_FROM, "esperado 'from'")
        from_tok = self._expect(TokenType.STRING, "esperado caminho em 'from'")
        library, macro = self._resolve_from(from_tok.value, from_tok.line)
        self._expect(TokenType.LBRACE, "esperado '{' no corpo do proc")
        self._expect(TokenType.KW_CODES, "esperado 'codes'")
        codes = self._parse_codes()
        self._expect(TokenType.RBRACE, "esperado '}' para fechar proc")
        return ProcDeclNode(name=name,
                            library=library,
                            macro=macro,
                            parameters=params,
                            output_codes=codes)

    def _parse_proc_block_body(
        self,
        name: str,
        params: list[ParamDeclNode],
        program_vars: set[str],
        declared_procs: dict[str, ProcDeclNode | ProcBlockNode],
    ) -> ProcBlockNode:
        """Parseia o corpo { exec ... } de um proc-bloco."""
        # Parâmetros ref funcionam como pseudo-variáveis dentro do corpo
        # Parâmetros lit também entram em body_vars para permitir uso como =nome_param
        body_vars = set(program_vars)
        for p in params:
            body_vars.add(p.name)
        self._pb_param_names = frozenset(p.name for p in params)
        self._expect(TokenType.LBRACE, "esperado '{' no corpo do proc-bloco")
        exec_block = self._parse_exec(
            declared_vars=body_vars,
            declared_procs=declared_procs,
            inherited_var=None,
            allow_arrow=False,
        )
        self._expect(TokenType.RBRACE, "esperado '}' para fechar proc-bloco")
        self._pb_param_names = frozenset()
        inferred_codes = list(exec_block.pass_codes)
        return ProcBlockNode(
            name=name,
            parameters=params,
            block=exec_block,
            inferred_codes=inferred_codes,
        )

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
        by_ref = False
        if self._check(TokenType.AMPERSAND):
            self._advance()
            by_ref = True
        type_tok = self._peek()
        if type_tok.type not in _TYPE_MAP:
            raise ParseError(f"tipo desconhecido '{type_tok.value}'", type_tok.line)
        self._advance()
        param_type = _TYPE_MAP[type_tok.type]
        if param_type == 'object' and by_ref:
            raise ParseError(
                "tipo 'Object' não suporta referência ('&'); remova o '&'",
                type_tok.line,
            )
        # Pluralidade — Type[] implica referência (usar & com [] é proibido)
        cardinality = 'singular'
        if self._check(TokenType.LBRACKET):
            if by_ref:
                raise ParseError(
                    "parâmetros plurais são sempre por referência; remova o '&'",
                    type_tok.line,
                )
            if param_type == 'object':
                raise ParseError(
                    "tipo 'Object' não suporta pluralidade ('[]')",
                    type_tok.line,
                )
            self._advance()
            self._expect(TokenType.RBRACKET, "esperado ']' após '['")
            cardinality = 'plural'
            by_ref = True  # plural → referência implícita
        evaluation = 'reference' if by_ref else 'literal'
        return ParamDeclNode(name=name_tok.value,
                             type=param_type,
                             cardinality=cardinality,
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
                    declared_procs: dict[str, ProcDeclNode | ProcBlockNode],
                    inherited_var: str | None,
                    allow_arrow: bool = True) -> ExecBlockNode:
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

        # as "nome" (opcional — deve vir ANTES de >>)
        block_name: str | None = None
        if self._check(TokenType.KW_AS):
            self._advance()
            name_tok = self._expect(TokenType.STRING, "esperado string após 'as'")
            block_name = name_tok.value

        # >> variavel (opcional — herança)
        variable: str | None = None
        variable_explicit = False
        if self._check(TokenType.ARROW):
            if not allow_arrow:
                raise ParseError(
                    "'>>' não é permitido no exec raiz de um proc-bloco",
                    self._peek().line,
                )
            self._advance()
            var_tok = self._expect(TokenType.IDENT, "esperado nome de variável após '>>'")
            # Validação semântica: variável deve estar declarada
            if var_tok.value not in declared_vars:
                raise ParseError(
                    f"variável '{var_tok.value}' não declarada em 'vars'",
                    var_tok.line,
                )
            variable = var_tok.value
            variable_explicit = True
            # Verificar se 'as' aparece DEPOIS de '>>' — ordem inválida
            if self._check(TokenType.KW_AS):
                raise ParseError(
                    "'as' deve vir antes de '>>': use exec proc() as \"nome\" >> var { }",
                    self._peek().line,
                )
        elif self._check(TokenType.KW_AS):
            # 'as' depois de '>>' — ordem inválida
            raise ParseError(
                "'as' deve vir antes de '>>': use exec proc() as \"nome\" >> var { }",
                self._peek().line,
            )
        else:
            variable = inherited_var

        self._expect(TokenType.LBRACE, "esperado '{' no corpo do exec")
        cases, pass_codes = self._parse_exec_body(
            proc_decl, declared_vars, declared_procs, variable
        )
        self._expect(TokenType.RBRACE, "esperado '}' para fechar exec")

        # while(...) aparece DEPOIS do }, não dentro do corpo
        loop_while: list[str] = []
        if self._check(TokenType.KW_WHILE):
            valid_codes = self._output_code_names(proc_decl)
            loop_while = self._parse_while(valid_codes)

        # Validação semântica: todos os códigos DO PROC ATUAL não tratados
        # devem aparecer em pass (pass pode conter também códigos borbulhados de filhos)
        valid_codes = self._output_code_names(proc_decl)
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
                      proc_decl: ProcDeclNode | ProcBlockNode,
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
                    raw = param.type == 'object'
                    kwargs[name_tok.value] = ArgNode(value=val_tok.value, evaluation='literal', raw=raw)
                elif val_tok.type == TokenType.NUMBER:
                    self._advance()
                    kwargs[name_tok.value] = ArgNode(value=int(val_tok.value), evaluation='literal')
                elif val_tok.type == TokenType.IDENT and val_tok.value in declared_vars:
                    # Placeholder lit de proc-bloco usado como valor: msg=nome_param
                    self._advance()
                    ev = 'placeholder' if val_tok.value in self._pb_param_names else 'literal'
                    kwargs[name_tok.value] = ArgNode(value=val_tok.value, evaluation=ev)
                else:
                    raise ParseError(f"valor inválido para argumento '{name_tok.value}'", val_tok.line)

        return kwargs

    def _parse_exec_body(
        self,
        proc_decl: ProcDeclNode | ProcBlockNode,
        declared_vars: set[str],
        declared_procs: dict[str, ProcDeclNode | ProcBlockNode],
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
                    declared_procs: dict[str, ProcDeclNode | ProcBlockNode],
                    inherited_var: str | None,
                    proc_decl: ProcDeclNode | ProcBlockNode) -> CaseNode:
        self._expect(TokenType.KW_CASE, "esperado 'case'")
        code_tok = self._expect(TokenType.IDENT, "esperado código após 'case'")
        # Não validamos o código contra proc_decl.output_codes aqui pois o motor
        # genjin permite capturar códigos borbulhados de procs filhos.
        self._expect(TokenType.COLON, "esperado ':' após código do case")
        child_block = self._parse_exec_or_inline(declared_vars, declared_procs, inherited_var)
        return CaseNode(output_code=code_tok.value, block=child_block)

    def _parse_while(self, valid_codes: set[str]) -> list[str]:
        self._expect(TokenType.KW_WHILE, "esperado 'while'")
        self._expect(TokenType.LPAREN, "esperado '(' após 'while'")
        codes: list[str] = []
        while not self._check(TokenType.RPAREN, TokenType.EOF):
            if codes:
                self._expect(TokenType.COMMA, "esperado ',' entre códigos no while")
            code_tok = self._expect(TokenType.IDENT, "esperado código no while")
            # Não validamos contra proc_decl.output_codes: o while pode incluir
            # códigos borbulhados de procs filhos (igual ao comportamento de pass).
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


def _parse_from_tokens(tokens: list) -> ProgramNode:
    """Parseia a partir de uma lista de tokens já produzida pelo scanner."""
    return Parser(tokens).parse()


if __name__ == '__main__':
    import argparse
    import sys
    from compiler.ast_io import tokens_from_json, ast_to_json
    from compiler.scanner import ScannerError

    ap = argparse.ArgumentParser(prog='python -m compiler.parser')
    ap.add_argument('tokens_file', nargs='?', help='arquivo JSON de tokens (padrão: stdin)')
    ap.add_argument('--source', metavar='ARQUIVO', help='arquivo .gnj (executa scanner+parser diretamente)')
    args = ap.parse_args()

    if args.source and args.tokens_file:
        ap.error('use --source OU arquivo de tokens, não os dois')

    try:
        if args.source:
            source = open(args.source, encoding='utf-8').read()
            ast = parse(source)
        else:
            raw = open(args.tokens_file, encoding='utf-8').read() if args.tokens_file else sys.stdin.read()
            tokens = tokens_from_json(raw)
            ast = _parse_from_tokens(tokens)
    except OSError as exc:
        print(f'Erro ao ler arquivo: {exc}', file=sys.stderr)
        sys.exit(2)
    except ScannerError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except ParseError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(ast_to_json(ast))
