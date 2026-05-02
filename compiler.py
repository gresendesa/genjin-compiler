#!/usr/bin/env python
"""
compiler.py — Pipeline completo do compilador Genjin.

Uso:
    python compiler.py [arquivo.gnj]
    python compiler.py [arquivo.gnj] -o saida.jinja2
    cat programa.gnj | python compiler.py

Saída: template Jinja2 gerado pelo transpiler.
Erros de sintaxe/parse: stderr, exit 1.
Erros de I/O: stderr, exit 2.
"""

import argparse
import sys

from compiler.scanner import Scanner, ScannerError
from compiler.parser import parse, ParseError
from compiler.desugar import desugar, DesugarError
from compiler.transpiler import Transpiler


def main() -> int:
    ap = argparse.ArgumentParser(
        prog='compiler.py',
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
    args = ap.parse_args()

    # Leitura da entrada
    try:
        if args.source_file:
            source = open(args.source_file, encoding='utf-8').read()
        else:
            source = sys.stdin.read()
    except OSError as exc:
        print(f'Erro ao ler entrada: {exc}', file=sys.stderr)
        return 2

    # Compilação
    try:
        ast = parse(source)
        ast = desugar(ast)
        result = Transpiler(ast).transpile()
    except ScannerError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ParseError as exc:
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
