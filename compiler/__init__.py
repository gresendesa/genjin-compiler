# Pacote do compilador Genjin
"""
compiler — Pacote público do compilador Genjin.

API de alto nível para uso programático:

    from compiler import compile_gnj, CompilerConfig, FilesystemGnjResolver

    # Uso padrão (filesystem)
    jinja2_template = compile_gnj(source)

    # Uso com resolvedores customizados (ex: banco de dados)
    from jinja2 import DictLoader
    from assembler import render

    config = CompilerConfig(
        gnj_resolver=MinhaImplementacao(),
        template_loader=DictLoader({"genjin": conteudo_genjin}),
    )
    jinja2_template = compile_gnj(source, config=config)
    output = render(jinja2_template, loader=config.template_loader)
"""

from __future__ import annotations

from pathlib import Path

from compiler.config import CompilerConfig, FilesystemGnjResolver, GnjSourceResolver
from compiler.scanner import Scanner, ScannerError
from compiler.parser import parse, ParseError
from compiler.resolve_imports import resolve_imports, ResolveImportError
from compiler.desugar import desugar, DesugarError
from compiler.transpiler import Transpiler

__all__ = [
    # API principal
    "compile_gnj",
    # Configuração e extensão
    "CompilerConfig",
    "GnjSourceResolver",
    "FilesystemGnjResolver",
    # Erros
    "ScannerError",
    "ParseError",
    "ResolveImportError",
    "DesugarError",
]


def compile_gnj(
    source: str,
    base_dir: Path | str | None = None,
    config: CompilerConfig | None = None,
) -> str:
    """Executa o pipeline completo do compilador Genjin e retorna o template Jinja2.

    Parâmetros:
        source   — código-fonte .gnj como string.
        base_dir — diretório base para resolução de imports via filesystem.
                   Ignorado quando config.gnj_resolver é fornecido.
                   Padrão: Path.cwd().
        config   — CompilerConfig com resolvedores customizados.
                   Se None, usa implementações filesystem padrão.

    Retorna o template Jinja2 gerado pelo transpiler (string).

    Levanta ScannerError, ParseError, ResolveImportError ou DesugarError em caso de erro.

    Exemplo simples:
        from compiler import compile_gnj
        resultado = compile_gnj(open("programa.gnj").read())

    Exemplo com config customizada:
        from compiler import compile_gnj, CompilerConfig
        from jinja2 import DictLoader

        config = CompilerConfig(
            gnj_resolver=MeuResolver(),
            template_loader=DictLoader({"genjin": template_genjin}),
        )
        resultado = compile_gnj(source, config=config)
    """
    cfg = config or CompilerConfig()

    if isinstance(base_dir, str):
        base_dir = Path(base_dir)

    ast = parse(source)
    ast = resolve_imports(
        ast,
        base_dir=base_dir,
        gnj_resolver=cfg.gnj_resolver,
    )
    ast = desugar(ast)
    return Transpiler(ast, template_name=cfg.compiler_template_name).transpile()
