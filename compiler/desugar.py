"""
Etapa 2.5: Desaçucaramento (Desugar)

Transforma nós inline (InlineAtomNode, InlineSeqNode) na AST canônica
(ExecBlockNode, CaseNode) antes da transpilação.

Pipeline: Source → Scanner → Parser → **Desugar** → Transpiler → Assembler

Decisão de arquitetura: DEC-001 (fase separada entre parser e transpiler).
Sintaxe aprovada: when(CODE) — DEC-002.
"""

from __future__ import annotations

from compiler.parser import (
    ArgNode,
    CaseNode,
    ExecBlockNode,
    InlineAtomNode,
    InlineSeqNode,
    ProcDeclNode,
    ProgramNode,
)


class DesugarError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


# ---------------------------------------------------------------------------
# Ponto de entrada público
# ---------------------------------------------------------------------------

def desugar(ast: ProgramNode) -> ProgramNode:
    """Percorre a AST e expande todos os nós inline para a forma canônica.

    Retorna um novo ProgramNode cujo bloco raiz é sempre ExecBlockNode.
    O ProgramNode original não é modificado.
    """
    proc_map: dict[str, ProcDeclNode] = {p.name: p for p in ast.procedures}
    block = _desugar_block(ast.block, proc_map,
                           pass_context=None,
                           inherited_var=None)
    return ProgramNode(
        name=ast.name,
        variables=ast.variables,
        procedures=ast.procedures,
        block=block,
    )


# ---------------------------------------------------------------------------
# Dispatcher: ExecBlockNode | InlineSeqNode → ExecBlockNode
# ---------------------------------------------------------------------------

def _desugar_block(
    node: ExecBlockNode | InlineSeqNode,
    proc_map: dict[str, ProcDeclNode],
    pass_context: list[str] | None,
    inherited_var: str | None,
) -> ExecBlockNode:
    if isinstance(node, InlineSeqNode):
        return _desugar_seq(node, proc_map, pass_context, inherited_var)
    if isinstance(node, ExecBlockNode):
        return _desugar_exec(node, proc_map)
    raise DesugarError(f"Nó desconhecido na AST: {type(node).__name__}")


# ---------------------------------------------------------------------------
# Desugar de ExecBlockNode canônico (recursão nas cases)
# ---------------------------------------------------------------------------

def _desugar_exec(
    node: ExecBlockNode,
    proc_map: dict[str, ProcDeclNode],
) -> ExecBlockNode:
    """Recursivamente desugar as cases de um ExecBlockNode já canônico."""
    new_cases: list[CaseNode] = []
    for case in node.cases:
        new_block = _desugar_block(
            case.block,
            proc_map,
            pass_context=node.pass_codes,
            inherited_var=node.variable,
        )
        new_cases.append(CaseNode(output_code=case.output_code, block=new_block))

    return ExecBlockNode(
        proc_name=node.proc_name,
        kwargs=node.kwargs,
        variable=node.variable,
        variable_explicit=node.variable_explicit,
        block_name=node.block_name,
        cases=new_cases,
        loop_while=node.loop_while,
        pass_codes=node.pass_codes,
    )


# ---------------------------------------------------------------------------
# Desugar de InlineSeqNode
# ---------------------------------------------------------------------------

def _desugar_seq(
    seq: InlineSeqNode,
    proc_map: dict[str, ProcDeclNode],
    pass_context: list[str] | None,
    inherited_var: str | None,
) -> ExecBlockNode:
    """Expande uma sequência inline para ExecBlockNode canônico.

    Algoritmo (S7-T02, DEC-002):
    1. Calcular var efetiva para cada átomo (esquerda → direita).
    2. Construir blocos da direita para a esquerda.
       - Terminal (@proc() sem when): pass_set = pass_context | codes(proc) - while_set
       - Chained (@proc() when(CODE)): pass_set = codes(proc) - {CODE} - while_set
       - Terminal ExecBlockNode: desugared recursivamente (pass_context não se aplica).
    """
    all_atoms: list[InlineAtomNode | ExecBlockNode] = list(seq.chained) + [seq.terminal]

    # Passo 1: resolver var efetiva para cada posição (esquerda → direita)
    effective_vars: list[str | None] = []
    cur_var = inherited_var
    for atom in all_atoms:
        if isinstance(atom, InlineAtomNode):
            v = atom.variable if atom.variable_explicit else cur_var
            effective_vars.append(v)
            cur_var = v  # propaga para o próximo
        else:
            # ExecBlockNode canônico — usa a var já resolvida pelo parser
            effective_vars.append(atom.variable)
            cur_var = atom.variable

    # Passo 2: construir da direita para a esquerda
    last = all_atoms[-1]
    last_var = effective_vars[-1]

    if isinstance(last, ExecBlockNode):
        inner: ExecBlockNode = _desugar_exec(last, proc_map)
    else:
        inner = _build_terminal(last, last_var, proc_map, pass_context)

    for i in range(len(seq.chained) - 1, -1, -1):
        atom = seq.chained[i]
        atom_var = effective_vars[i]
        inner = _build_chained(atom, atom_var, inner, proc_map)

    return inner


# ---------------------------------------------------------------------------
# Construtores de nós canônicos
# ---------------------------------------------------------------------------

def _build_terminal(
    atom: InlineAtomNode,
    var: str | None,
    proc_map: dict[str, ProcDeclNode],
    pass_context: list[str] | None = None,  # mantido por compatibilidade, não usado
) -> ExecBlockNode:
    """Constrói o ExecBlockNode para um átomo terminal (sem when_code).

    pass_set = codes(proc) - while_set
    O terminal sempre passa todos os códigos do proc que não estão em while.
    """
    while_set = {atom.while_code} if atom.while_code else set()
    proc_decl = _get_proc(atom.proc_name, proc_map)
    all_codes = {oc.name for oc in proc_decl.output_codes}
    pass_set = all_codes - while_set

    return ExecBlockNode(
        proc_name=atom.proc_name,
        kwargs=atom.kwargs,
        variable=var,
        variable_explicit=atom.variable_explicit,
        block_name=None,
        cases=[],
        loop_while=sorted(while_set),
        pass_codes=sorted(pass_set),
    )


def _build_chained(
    atom: InlineAtomNode,
    var: str | None,
    inner: ExecBlockNode,
    proc_map: dict[str, ProcDeclNode],
) -> ExecBlockNode:
    """Constrói o ExecBlockNode para um átomo encadeado (tem when_code).

    pass_set = codes(proc) - {when_code} - while_set
    """
    assert atom.when_code is not None
    while_set = {atom.while_code} if atom.while_code else set()
    when_code = atom.when_code

    proc_decl = _get_proc(atom.proc_name, proc_map)
    all_codes = {oc.name for oc in proc_decl.output_codes}
    pass_set = all_codes - {when_code} - while_set

    return ExecBlockNode(
        proc_name=atom.proc_name,
        kwargs=atom.kwargs,
        variable=var,
        variable_explicit=atom.variable_explicit,
        block_name=None,
        cases=[CaseNode(output_code=when_code, block=inner)],
        loop_while=sorted(while_set),
        pass_codes=sorted(pass_set),
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_proc(name: str, proc_map: dict[str, ProcDeclNode]) -> ProcDeclNode:
    proc = proc_map.get(name)
    if proc is None:
        raise DesugarError(f"Procedimento '{name}' referenciado em notação inline não encontrado em 'procs'")
    return proc
