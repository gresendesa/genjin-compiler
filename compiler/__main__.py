"""
compiler/__main__.py — Entry point do compilador Genjin como pacote instalável.

Permite:
    python -m compiler [arquivo.gnj]
    genjin-compile [arquivo.gnj]     (quando instalado via pip)
"""

import sys
from pathlib import Path

import argparse

from compiler.scanner import Scanner, ScannerError
from compiler.parser import parse, ParseError
from compiler.resolve_imports import resolve_imports, ResolveImportError
from compiler.desugar import desugar, DesugarError
from compiler.transpiler import Transpiler


def main() -> int:
    ap = argparse.ArgumentParser(
        prog='genjin-compile',
        description='Compilador Genjin: .gnj → template Jinja2',
    )
    ap.add_argument(
        'source_file',
        nargs='?',
        metavar='ARQUIVO',
        help='arquivo .gnj de entrada (padrão: stdin)',
    )
    ap.add_argument(
        '-o', '--output',
        metavar='SAIDA',
        help='arquivo de saída (padrão: stdout)',
    )
    ap.add_argument(
        '--import-base',
        metavar='DIR',
        help='diretório base para resolução de importações (padrão: diretório do arquivo fonte)',
    )
    args = ap.parse_args()

    # Leitura da entrada
    try:
        if args.source_file:
            source = open(args.source_file, encoding='utf-8').read()
            source_path = Path(args.source_file).resolve()
        else:
            source = sys.stdin.read()
            source_path = None
    except OSError as exc:
        print(f'Erro ao ler entrada: {exc}', file=sys.stderr)
        return 2

    # Determinar diretório base para importações
    if args.import_base:
        import_base = Path(args.import_base).resolve()
    elif source_path is not None:
        import_base = source_path.parent
    else:
        import_base = Path.cwd()

    # Compilação
    try:
        ast = parse(source)
        ast = resolve_imports(ast, base_dir=import_base)
        ast = desugar(ast)
        result = Transpiler(ast).transpile()
    except ScannerError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ParseError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ResolveImportError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except DesugarError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    # Escrita da saída
    try:
        if args.output:
            open(args.output, 'w', encoding='utf-8').write(result)
        else:
            print(result, end='')
    except OSError as exc:
        print(f'Erro ao escrever saída: {exc}', file=sys.stderr)
        return 2

    return 0


if __name__ == '__main__':
    sys.exit(main())
