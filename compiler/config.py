"""
compiler/config.py — Configuração pública do compilador Genjin.

Expõe os pontos de extensão que permitem customizar:
1. O resolvedor de source .gnj para imports (GnjSourceResolver)
2. O Jinja2 loader para o assembler (template_loader)
3. O nome do template base emitido pelo transpiler (compiler_template_name)

Uso básico (filesystem padrão):
    from compiler import compile_gnj
    result = compile_gnj(source)

Uso com resolvedores customizados (ex: banco de dados):
    from compiler.config import CompilerConfig, GnjSourceResolver
    from jinja2 import DictLoader

    class DbGnjResolver:
        def get_source(self, dotted_path: str) -> str:
            return db.fetch_gnj(dotted_path)

    config = CompilerConfig(
        gnj_resolver=DbGnjResolver(),
        template_loader=DictLoader({"genjin": db.fetch_template("genjin")}),
    )
    result = compile_gnj(source, config=config)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from jinja2 import BaseLoader


@runtime_checkable
class GnjSourceResolver(Protocol):
    """Protocolo para resolução de source de arquivos .gnj por caminho dotted.

    Implementações devem levantar FileNotFoundError (ou similar) quando
    o caminho não for encontrado.
    """

    def get_source(self, dotted_path: str) -> str:
        """Retorna o source do arquivo .gnj identificado por dotted_path.

        dotted_path: caminho no formato 'a.b.c' (sem extensão .gnj).
        """
        ...  # pragma: no cover


class FilesystemGnjResolver:
    """Implementação padrão: resolve .gnj a partir do sistema de arquivos.

    Converte 'a.b.c' → base_dir/a/b/c.gnj e retorna o conteúdo.
    """

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()

    def get_source(self, dotted_path: str) -> str:
        parts = dotted_path.split('.')
        file_path = self.base_dir.joinpath(*parts).with_suffix('.gnj')
        return file_path.read_text(encoding='utf-8')


@dataclass
class CompilerConfig:
    """Configuração central do compilador Genjin.

    Todos os campos são opcionais. Quando None, a implementação padrão
    (baseada em sistema de arquivos) é utilizada.

    Exemplo — compilar com resolvedores customizados:

        config = CompilerConfig(
            gnj_resolver=MinhaImplementacao(),
            template_loader=DictLoader({"genjin": conteudo_do_template}),
        )
        resultado = compile_gnj(source, config=config)
    """

    gnj_resolver: GnjSourceResolver | None = None
    """Resolvedor de source .gnj para `from X import Y`.
    Padrão: FilesystemGnjResolver com base_dir=diretório do arquivo fonte.
    """

    template_loader: BaseLoader | None = None
    """Jinja2 loader para o assembler. Cobre a resolução de genjin.jinja2
    e dos demais templates do projeto (árvore code/).
    Padrão: DottedLoader(FileSystemLoader(cwd)).
    """

    compiler_template_name: str = "genjin"
    """Nome do template base emitido pelo transpiler em '{* from "X" import ... *}'.
    Alterar apenas se o template base tiver um nome diferente de 'genjin' no seu loader.
    Padrão: 'genjin'.
    """
