"""
Etapa 2.5: Desaçucaramento (Desugar)

Transforma nós inline (InlineAtomNode, InlineSeqNode) na AST canônica
(ExecBlockNode, CaseNode) antes da transpilação.

Pipeline: Source → Scanner → Parser → **Desugar** → Transpiler → Assembler

Decisão de arquitetura: DEC-001 (fase separada entre parser e transpiler).
Sintaxe aprovada: when(CODE) — DEC-002.
"""

from __future__ import annotations

import copy

from compiler.parser import (
    ArgNode,
    CaseNode,
    ExecBlockNode,
    InlineAtomNode,
    InlineSeqNode,
    ProcBlockNode,
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
    """Percorre a AST e expande todos os nós inline e proc-blocos para a forma canônica.

    Retorna um novo ProgramNode cujo bloco raiz é sempre ExecBlockNode.
    Proc-blocos são filtrados de `procedures` no resultado final.
    O ProgramNode original não é modificado.
    """
    proc_map: dict[str, ProcDeclNode | ProcBlockNode] = {p.name: p for p in ast.procedures}
    block_map: dict[str, ProcBlockNode] = {
        p.name: p for p in ast.procedures if isinstance(p, ProcBlockNode)
    }

    # S12-T09: detectar ciclos e obter ordem topológica (folhas primeiro)
    topo_order = _topo_proc_blocks(block_map)

    # S12-T11: expandir proc-blocos em ordem topológica
    for pb_name in topo_order:
        pb = block_map[pb_name]
        expanded_body = _desugar_exec(pb.block, proc_map)
        expanded_pb = ProcBlockNode(
            name=pb.name,
            parameters=pb.parameters,
            block=expanded_body,
            inferred_codes=pb.inferred_codes,
        )
        proc_map[pb_name] = expanded_pb
        block_map[pb_name] = expanded_pb

    block = _desugar_block(ast.block, proc_map, pass_context=None, inherited_var=None)

    # S12-T12: filtrar proc-blocos de procedures
    procedures = [p for p in ast.procedures if isinstance(p, ProcDeclNode)]

    return ProgramNode(
        name=ast.name,
        variables=ast.variables,
        procedures=procedures,
        block=block,
    )


# ---------------------------------------------------------------------------
# Dispatcher: ExecBlockNode | InlineSeqNode → ExecBlockNode
# ---------------------------------------------------------------------------

def _desugar_block(
    node: ExecBlockNode | InlineSeqNode,
    proc_map: dict[str, ProcDeclNode | ProcBlockNode],
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
    proc_map: dict[str, ProcDeclNode | ProcBlockNode],
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
    proc_map: dict[str, ProcDeclNode | ProcBlockNode],
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
    proc_map: dict[str, ProcDeclNode | ProcBlockNode],
    pass_context: list[str] | None = None,  # mantido por compatibilidade, não usado
) -> ExecBlockNode:
    """Constrói o ExecBlockNode para um átomo terminal (sem when_code).

    Para ProcDeclNode: pass_set = codes(proc) - while_set
    Para ProcBlockNode: expande o corpo do bloco substituindo parâmetros.
    """
    proc = _get_proc(atom.proc_name, proc_map)

    if isinstance(proc, ProcBlockNode):
        cloned = _expand_proc_block(proc, atom.kwargs)
        # Corpo do proc-bloco não tem >> (proibido); herdar var do contexto de chamada
        return ExecBlockNode(
            proc_name=cloned.proc_name,
            kwargs=cloned.kwargs,
            variable=var,
            variable_explicit=atom.variable_explicit,
            block_name=cloned.block_name,
            cases=cloned.cases,
            loop_while=cloned.loop_while,
            pass_codes=cloned.pass_codes,
        )

    while_set = {atom.while_code} if atom.while_code else set()
    all_codes = {oc.name for oc in proc.output_codes}
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
    proc_map: dict[str, ProcDeclNode | ProcBlockNode],
) -> ExecBlockNode:
    """Constrói o ExecBlockNode para um átomo encadeado (tem when_code).

    Para ProcDeclNode: pass_set = codes(proc) - {when_code} - while_set
    Para ProcBlockNode: expande o corpo e injeta 'inner' no case when_code.
    """
    assert atom.when_code is not None
    proc = _get_proc(atom.proc_name, proc_map)

    if isinstance(proc, ProcBlockNode):
        cloned = _expand_proc_block(proc, atom.kwargs)
        when_code = atom.when_code
        if when_code not in cloned.pass_codes:
            raise DesugarError(
                f"código '{when_code}' não está nos códigos de saída inferidos "
                f"do proc-bloco '{atom.proc_name}'"
            )
        new_pass = [c for c in cloned.pass_codes if c != when_code]
        new_cases = list(cloned.cases) + [CaseNode(output_code=when_code, block=inner)]
        return ExecBlockNode(
            proc_name=cloned.proc_name,
            kwargs=cloned.kwargs,
            variable=var,
            variable_explicit=atom.variable_explicit,
            block_name=cloned.block_name,
            cases=new_cases,
            loop_while=cloned.loop_while,
            pass_codes=new_pass,
        )

    while_set = {atom.while_code} if atom.while_code else set()
    when_code = atom.when_code

    all_codes = {oc.name for oc in proc.output_codes}
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

def _get_proc(name: str, proc_map: dict[str, ProcDeclNode | ProcBlockNode]) -> ProcDeclNode | ProcBlockNode:
    proc = proc_map.get(name)
    if proc is None:
        raise DesugarError(f"Procedimento '{name}' referenciado em notação inline não encontrado em 'procs'")
    return proc


# ---------------------------------------------------------------------------
# S12-T09: DFS anti-ciclo entre proc-blocos + ordem topológica
# ---------------------------------------------------------------------------

def _topo_proc_blocks(block_map: dict[str, ProcBlockNode]) -> list[str]:
    """DFS para detectar ciclos entre proc-blocos e retornar ordem topológica (folhas primeiro).

    Levanta DesugarError com o caminho do ciclo se recursão for detectada.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {name: WHITE for name in block_map}
    topo: list[str] = []
    path: list[str] = []

    def _dfs(name: str) -> None:
        color[name] = GRAY
        path.append(name)
        deps: list[str] = []
        _collect_proc_block_refs(block_map[name].block, block_map, deps)
        for dep in deps:
            if color.get(dep) == GRAY:
                cycle_start = path.index(dep)
                cycle = path[cycle_start:] + [dep]
                raise DesugarError(
                    "recursão detectada em proc-blocos: " + " → ".join(cycle)
                )
            if color.get(dep) == WHITE:
                _dfs(dep)
        path.pop()
        color[name] = BLACK
        topo.append(name)

    for name in block_map:
        if color[name] == WHITE:
            _dfs(name)

    return topo  # ordem topológica: folhas primeiro


def _collect_proc_block_refs(
    node: ExecBlockNode | InlineSeqNode,
    block_map: dict[str, ProcBlockNode],
    result: list[str],
) -> None:
    """Coleta nomes de proc-blocos referenciados no corpo de um nó (recursivo)."""
    if isinstance(node, ExecBlockNode):
        if node.proc_name in block_map:
            result.append(node.proc_name)
        for case in node.cases:
            _collect_proc_block_refs(case.block, block_map, result)
    elif isinstance(node, InlineSeqNode):
        for atom in node.chained:
            if isinstance(atom, InlineAtomNode) and atom.proc_name in block_map:
                result.append(atom.proc_name)
        if isinstance(node.terminal, InlineAtomNode):
            if node.terminal.proc_name in block_map:
                result.append(node.terminal.proc_name)
        elif isinstance(node.terminal, ExecBlockNode):
            _collect_proc_block_refs(node.terminal, block_map, result)


# ---------------------------------------------------------------------------
# S12-T10: Expansão de proc-bloco (deep clone + visitor de substituição)
# ---------------------------------------------------------------------------

def _expand_proc_block(
    pb: ProcBlockNode,
    call_kwargs: dict[str, ArgNode],
) -> ExecBlockNode:
    """Deep clone o corpo do proc-bloco e substitui ArgNodes placeholder pelos valores da chamada."""
    cloned: ExecBlockNode = copy.deepcopy(pb.block)
    subst: dict[str, ArgNode] = {
        p.name: call_kwargs[p.name]
        for p in pb.parameters
        if p.name in call_kwargs
    }
    _substitute_params(cloned, subst)
    return cloned


def _substitute_params(
    node: ExecBlockNode | InlineSeqNode,
    subst: dict[str, ArgNode],
) -> None:
    """Visitor in-place: substitui ArgNodes cujo value é nome de placeholder."""
    if isinstance(node, ExecBlockNode):
        for key in list(node.kwargs):
            arg = node.kwargs[key]
            # 'reference' cobre &param_ref; 'placeholder' cobre lit param usado como IDENT
            if arg.evaluation in ('reference', 'placeholder') and arg.value in subst:
                node.kwargs[key] = subst[arg.value]
        for case in node.cases:
            _substitute_params(case.block, subst)
    elif isinstance(node, InlineSeqNode):
        for atom in node.chained:
            _substitute_params_atom(atom, subst)
        if isinstance(node.terminal, InlineAtomNode):
            _substitute_params_atom(node.terminal, subst)
        else:
            _substitute_params(node.terminal, subst)


def _substitute_params_atom(atom: InlineAtomNode, subst: dict[str, ArgNode]) -> None:
    """Visitor in-place para InlineAtomNode."""
    for key in list(atom.kwargs):
        arg = atom.kwargs[key]
        if arg.evaluation in ('reference', 'placeholder') and arg.value in subst:
            atom.kwargs[key] = subst[arg.value]

