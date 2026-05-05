"""
Etapa 2.7: Resolução de importações (ResolveImports)

Substitui cada ProcImportNode da AST pelos ProcBlockNode concretos
carregados dos arquivos .gnj referenciados.

Pipeline: Source → Scanner → Parser → **ResolveImports** → Desugar → Transpiler → Assembler
"""

from __future__ import annotations

from pathlib import Path

from compiler.parser import (
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
    """Resolve todos os ProcImportNode da AST, substituindo-os pelos ProcBlockNode concretos.

    Parâmetros:
        ast      — AST produzida pelo parser (pode conter ProcImportNode).
        base_dir — diretório base para resolução de paths dotted.
                   Se None, usa Path.cwd().

    Retorna um novo ProgramNode sem nenhum ProcImportNode.
    Levanta ResolveImportError em caso de:
        - arquivo não encontrado
        - nome solicitado não existe no arquivo externo
        - conflito de nome com proc já declarado localmente
        - importação circular
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Conjunto de paths absolutos em visita (detecção de ciclos)
    visiting: set[Path] = set()

    return _resolve_ast(ast, base_dir, visiting)


def _dotted_to_path(dotted: str, base_dir: Path) -> Path:
    """Converte 'a.b.c' → base_dir/a/b/c.gnj."""
    parts = dotted.split('.')
    return base_dir.joinpath(*parts).with_suffix('.gnj')


def _resolve_ast(ast: ProgramNode, base_dir: Path, visiting: set[Path]) -> ProgramNode:
    """Resolve os ProcImportNode de um ProgramNode, retornando nova lista de procedures."""
    # Coletar nomes dos procs não-import já declarados neste arquivo
    local_names: set[str] = {
        p.name for p in ast.procedures
        if isinstance(p, (ProcDeclNode, ProcBlockNode))
    }

    resolved: list[ProcDeclNode | ProcBlockNode | ProcImportNode] = []
    for entry in ast.procedures:
        if not isinstance(entry, ProcImportNode):
            resolved.append(entry)
            continue

        # Resolver caminho
        gnj_path = _dotted_to_path(entry.source_path, base_dir).resolve()

        # Verificar ciclo
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

        # Indexar proc-blocos disponíveis no arquivo externo
        external_blocks: dict[str, ProcBlockNode] = {
            p.name: p
            for p in external_ast.procedures
            if isinstance(p, ProcBlockNode)
        }

        # Importar os nomes solicitados
        for name in entry.names:
            # Verificar conflito com local
            if name in local_names:
                raise ResolveImportError(
                    f"conflito de nome: '{name}' já está declarado localmente "
                    f"e não pode ser importado de '{entry.source_path}'"
                )
            # Verificar existência no externo
            if name not in external_blocks:
                raise ResolveImportError(
                    f"proc-bloco '{name}' não encontrado em '{entry.source_path}' ({gnj_path})"
                )
            resolved.append(external_blocks[name])
            local_names.add(name)

    return ProgramNode(
        name=ast.name,
        variables=ast.variables,
        procedures=resolved,
        block=ast.block,
    )
