"""
assembler.py — Renderizador de templates Jinja2

Uso básico:
    python assembler.py <template> -d <diretório> -o <saída> [opções]

Exemplos:
    # Renderizar com diretório de templates e saída
    python assembler.py implementation.jinja2 -d ./templates -o output.js

    # Passar variáveis inline
    python assembler.py main.j2 -d ./tpl -o result.txt -v nome=Mundo -v versao=2

    # Usar arquivo JSON com variáveis
    python assembler.py main.j2 -d ./tpl -o result.txt -f vars.json

    # Usar delimitadores customizados (padrão deste projeto: {* *})
    python assembler.py impl.jinja2 -d . -o out.js --block-start '{*' --block-end '*}'

Delimitadores customizados padrão deste projeto:
    --block-start '{*'  --block-end '*}'
    (variáveis e comentários permanecem {{ }}, {# #})
"""

import argparse
import json
import os
import sys
import random

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError


class Cortex:
    '''
    Classe para envelopar funcionalidades 
    no ambiente Cortex
    '''
    counter = random.randint(1000000, 9999999)
    def get_next_number():
        Cortex.counter += 1
        number = Cortex.counter
        return str(hex(number)).lower()[2:]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="assembler",
        description="Renderiza um template Jinja2 usando um diretório de templates e grava a saída em arquivo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "template",
        help=(
            "Caminho para o arquivo de template principal (ponto de entrada). "
            "Pode ser um caminho absoluto ou relativo ao diretório de templates (-d)."
        ),
    )
    parser.add_argument(
        "-d", "--templates-dir",
        metavar="DIR",
        default=None,
        help=(
            "Diretório raiz dos templates. Templates referenciados por extends/include/import "
            "são resolvidos relativamente a este diretório. "
            "Se omitido, usa o diretório do arquivo de template."
        ),
    )
    parser.add_argument(
        "-o", "--output",
        metavar="ARQUIVO",
        required=True,
        help="Caminho do arquivo de saída que receberá o conteúdo renderizado.",
    )
    parser.add_argument(
        "-v", "--var",
        metavar="CHAVE=VALOR",
        action="append",
        dest="vars",
        default=[],
        help=(
            "Define uma variável para o contexto do template no formato CHAVE=VALOR. "
            "Pode ser repetido: -v nome=Mundo -v versao=2"
        ),
    )
    parser.add_argument(
        "-f", "--vars-file",
        metavar="JSON",
        default=None,
        help=(
            "Arquivo JSON com variáveis a serem injetadas no contexto do template. "
            "Mesclado com as variáveis definidas por -v (que têm precedência)."
        ),
    )

    delimiters = parser.add_argument_group("delimitadores customizados")
    delimiters.add_argument("--block-start",    default="{*", metavar="STR", help="Início de bloco (padrão: '{%%')")
    delimiters.add_argument("--block-end",      default="*}", metavar="STR", help="Fim de bloco (padrão: '%%}')")
    delimiters.add_argument("--variable-start", default="{{", metavar="STR", help="Início de variável (padrão: '{{')")
    delimiters.add_argument("--variable-end",   default="}}", metavar="STR", help="Fim de variável (padrão: '}}')")
    delimiters.add_argument("--comment-start",  default="{!!", metavar="STR", help="Início de comentário (padrão: '{#')")
    delimiters.add_argument("--comment-end",    default="!!}", metavar="STR", help="Fim de comentário (padrão: '#}')")

    return parser.parse_args()


def build_context(var_list: list[str], vars_file: str | None) -> dict:
    """Constrói o dicionário de contexto a partir de arquivo JSON e/ou pares CHAVE=VALOR."""
    context: dict = {}

    if vars_file:
        if not os.path.isfile(vars_file):
            sys.exit(f"Erro: arquivo de variáveis não encontrado: {vars_file!r}")
        with open(vars_file, encoding="utf-8") as fh:
            try:
                loaded = json.load(fh)
            except json.JSONDecodeError as exc:
                sys.exit(f"Erro ao ler {vars_file!r}: {exc}")
        if not isinstance(loaded, dict):
            sys.exit(f"Erro: {vars_file!r} deve conter um objeto JSON no nível raiz.")
        context.update(loaded)

    for pair in var_list:
        if "=" not in pair:
            sys.exit(f"Erro: variável inválida {pair!r}. Use o formato CHAVE=VALOR.")
        key, _, value = pair.partition("=")
        context[key.strip()] = value

    return context


def resolve_template_name(template_path: str, templates_dir: str) -> str:
    """Retorna o nome do template relativo ao diretório de templates."""
    abs_template = os.path.abspath(template_path)
    abs_dir = os.path.abspath(templates_dir)
    try:
        return os.path.relpath(abs_template, abs_dir)
    except ValueError:
        # No Windows, relpath falha entre drives distintos
        return os.path.basename(template_path)


def main() -> None:
    args = parse_args()

    # Resolve o diretório de templates
    if args.templates_dir:
        templates_dir = os.path.abspath(args.templates_dir)
    else:
        templates_dir = os.path.abspath(os.path.dirname(args.template) or ".")

    if not os.path.isdir(templates_dir):
        sys.exit(f"Erro: diretório de templates não encontrado: {templates_dir!r}")

    template_name = resolve_template_name(args.template, templates_dir)

    # Cria o ambiente Jinja2
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        block_start_string=args.block_start,
        block_end_string=args.block_end,
        variable_start_string=args.variable_start,
        variable_end_string=args.variable_end,
        comment_start_string=args.comment_start,
        comment_end_string=args.comment_end,
        keep_trailing_newline=True,
    )

    env.globals.update({
        "nid": Cortex.get_next_number,
    })

    # Carrega o template
    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        sys.exit(f"Erro: template não encontrado: {template_name!r} em {templates_dir!r}")
    except TemplateSyntaxError as exc:
        sys.exit(f"Erro de sintaxe no template {template_name!r} (linha {exc.lineno}): {exc.message}")

    # Monta o contexto de variáveis
    context = build_context(args.vars, args.vars_file)

    # Renderiza
    try:
        rendered = template.render(**context)
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"Erro durante a renderização: {exc}")

    # Grava a saída
    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(rendered)

    print(f"Saída gravada em: {output_path}")


if __name__ == "__main__":
    main()
