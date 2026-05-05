"""
Etapa 2.7: Resolução de importações (ResolveImports)

Substitui cada ProcImportNode da AST pelos nós concretos (ProcDeclNode ou
ProcBlockNode) carregados dos arquivos .gnj referenciados, injetando
automaticamente as dependências transitivas de cada proc-bloco importado.

Pipeline: Source → Scanner → Parser → **ResolveImports** → Desugar → Transpiler → Assembler
"""

from __future__ import annotations

from pathlib import Path

from compiler.parser import (
    ExecBlockNode,
    InlineAtomNode,
    InlineSeqNode,
    ProcBlockNode,
    ProcDeclNode,
    ProcImportNode,
    ProgramNode,
    parse,
)


class ResolveImportError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def resolve_imports(ast: ProgramNode, base_dir: Path | None = None) -> ProgramNode:
    """Resolve todos os ProcImportNode da AST, substituindo-os pelos nós concretos.

    Parâmetros:
        ast      — AST produzida pelo parser (pode conter ProcImportNode).
        base_dir — diretório base para resolução de paths dotted.
                   Se None, usa Path.cwd().

    Retorna um novo ProgramNode sem nenhum ProcImportNode.
    Levanta ResolveImportError em caso de:
        - arquivo não encontrado
        - nome solicitado não existe no arquivo externo
        - conflito de nome com proc já declarado localmente (definição diferente)
        - importação circular (entre arquivos)
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Conjunto de paths absolutos em visita (detecção de ciclos entre arquivos)
    visiting: set[Path] = set()

    return _resolve_ast(ast, base_dir, visiting)


def _dotted_to_path(dotted: str, base_dir: Path) -> Path:
    """Converte 'a.b.c' → base_dir/a/b/c.gnj."""
    parts = dotted.split('.')
    return base_dir.joinpath(*parts).with_suffix('.gnj')


def _collect_proc_names(body: ExecBlockNode | InlineSeqNode | InlineAtomNode) -> set[str]:
    """DFS sobre o corpo de um proc-bloco → conjunto de nomes de procs referenciados."""
    names: set[str] = set()

    def walk(node: ExecBlockNode | InlineSeqNode | InlineAtomNode) -> None:
        if isinstance(node, ExecBlockNode):
            names.add(node.proc_name)
            for case in node.cases:
                walk(case.block)
        elif isinstance(node, InlineSeqNode):
            for atom in node.chained:
                names.add(atom.proc_name)
            terminal = node.terminal
            if isinstance(terminal, InlineAtomNode):
                names.add(terminal.proc_name)
            else:
                walk(terminal)
        elif isinstance(node, InlineAtomNode):
            names.add(node.proc_name)

    walk(body)
    return names


def _inject_deps(
    pb: ProcBlockNode,
    external_map: dict[str, ProcDeclNode | ProcBlockNode],
    local_names: set[str],
    resolved: list[ProcDeclNode | ProcBlockNode],
    visiting_deps: set[str],
    source_path: str,
) -> None:
    """Injeta no arquivo importador todos os procs dos quais pb depende.

    - Deps já em local_names são ignoradas silenciosamente se a definição é idêntica.
    - Deps com definição diferente geram ResolveImportError.
    - Deps que são ProcBlockNode são processadas recursivamente.
    - visiting_deps previne ciclos defensivos durante a análise de dependências.
    """
    visiting_deps.add(pb.name)

    for dep_name in _collect_proc_names(pb.block):
        if dep_name in local_names:
            # Já existe localmente — verificar se é mesma definição
            existing = next((p for p in resolved if p.name == dep_name), None)
            if existing is not None and dep_name in external_map:
                if existing != external_map[dep_name]:
                    raise ResolveImportError(
                        f"conflito de definição ao injetar dependência '{dep_name}' "
                        f"de '{source_path}': definição local diverge do externo"
                    )
            continue

        if dep_name not in external_map:
            raise ResolveImportError(
                f"dependência '{dep_name}' de '{pb.name}' não encontrada "
                f"em '{source_path}'"
            )

        dep = external_map[dep_name]
        resolved.append(dep)
        local_names.add(dep_name)

        if isinstance(dep, ProcBlockNode) and dep.name not in visiting_deps:
            _inject_deps(dep, external_map, local_names, resolved, visiting_deps, source_path)

    visiting_deps.discard(pb.name)


def _resolve_ast(ast: ProgramNode, base_dir: Path, visiting: set[Path]) -> ProgramNode:
    """Resolve os ProcImportNode de um ProgramNode, retornando nova lista de procedures."""
    # Coletar nomes dos procs não-import já declarados neste arquivo
    local_names: set[str] = {
        p.name for p in ast.procedures
        if isinstance(p, (ProcDeclNode, ProcBlockNode))
    }

    resolved: list[ProcDeclNode | ProcBlockNode] = []
    for entry in ast.procedures:
        if not isinstance(entry, ProcImportNode):
            resolved.append(entry)
            continue

        # Resolver caminho
        gnj_path = _dotted_to_path(entry.source_path, base_dir).resolve()

        # Verificar ciclo entre arquivos
        if gnj_path in visiting:
            raise ResolveImportError(
                f"importação circular detectada: '{entry.source_path}' "
                f"({gnj_path}) já está sendo processado"
            )

        # Verificar existência
        if not gnj_path.exists():
            raise ResolveImportError(
                f"arquivo não encontrado para importação '{entry.source_path}': {gnj_path}"
            )

        # Parsear e resolver recursivamente o arquivo externo
        source = gnj_path.read_text(encoding='utf-8')
        external_ast = parse(source)
        visiting.add(gnj_path)
        try:
            external_ast = _resolve_ast(external_ast, gnj_path.parent, visiting)
        finally:
            visiting.discard(gnj_path)

        # Indexar todos os procs disponíveis no arquivo externo (ProcDecl e ProcBlock)
        external_map: dict[str, ProcDeclNode | ProcBlockNode] = {
            p.name: p
            for p in external_ast.procedures
            if isinstance(p, (ProcDeclNode, ProcBlockNode))
        }

        # Importar os nomes solicitados e injetar dependências
        for name in entry.names:
            # Verificar existência no externo
            if name not in external_map:
                raise ResolveImportError(
                    f"'{name}' não encontrado em '{entry.source_path}' ({gnj_path})"
                )
            node = external_map[name]
            # Verificar conflito com local (mesma definição é permitida)
            if name in local_names:
                existing = next((p for p in resolved if p.name == name), None)
                if existing is not None and existing != node:
                    raise ResolveImportError(
                        f"conflito de nome: '{name}' já está declarado localmente "
                        f"com definição diferente da importada de '{entry.source_path}'"
                    )
                # Já existe localmente com mesma definição — skip
                continue

            resolved.append(node)
            local_names.add(name)

            # Injetar dependências automaticamente se for proc-bloco
            if isinstance(node, ProcBlockNode):
                visiting_deps: set[str] = set()
                _inject_deps(node, external_map, local_names, resolved, visiting_deps, entry.source_path)

    return ProgramNode(
        name=ast.name,
        variables=ast.variables,
        procedures=resolved,
        block=ast.block,
    )

