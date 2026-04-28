"""
assembler.py — Renderizador de templates Jinja2

Uso básico:
    python assembler.py <template> -d <diretório> -o <saída> [opções]

Exemplos:
    # Renderizar com diretório de templates e saída
    python assembler.py implementation.jinja2 -d ./templates -o output.js

    # Ler template da entrada padrão (pipe)
    python compiler.py programa.gnj | python assembler.py - -d ./code -o saida.txt
    echo '{{ nome }}' | python assembler.py - -v nome=Mundo -o saida.txt

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

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError


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
            "Pode ser um caminho absoluto ou relativo ao diretório de templates (-d). "
            "Use '-' para ler o template da entrada padrão (stdin)."
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


class DottedLoader(FileSystemLoader):
    """Loader que resolve nomes com '.' como separadores de diretório.

    Converte 'Federal.text.chat' → 'Federal/text/chat.jinja2'.
    Se o nome já tiver extensão, apenas converte os separadores.
    """

    TEMPLATE_EXT = ".jinja2"

    def get_source(self, environment, template):
        if template.endswith(self.TEMPLATE_EXT):
            stem = template[: -len(self.TEMPLATE_EXT)]
        else:
            stem = template
        path = stem.replace(".", "/") + self.TEMPLATE_EXT
        return super().get_source(environment, path)


def resolve_template_name(template_path: str, templates_dir: str) -> str:
    """Retorna o nome do template relativo ao diretório de templates.

    Usa '.' como separador de nível e omite a extensão '.jinja2'.
    Exemplo: 'code/Federal/text/chat.jinja2' → 'Federal.text.chat'
    """
    abs_template = os.path.abspath(template_path)
    abs_dir = os.path.abspath(templates_dir)
    try:
        rel = os.path.relpath(abs_template, abs_dir)
    except ValueError:
        # No Windows, relpath falha entre drives distintos
        rel = os.path.basename(template_path)
    rel = rel.replace(os.sep, "/")
    stem, ext = os.path.splitext(rel)
    dotted = stem.replace("/", ".")
    if ext != DottedLoader.TEMPLATE_EXT:
        dotted += ext
    return dotted


def main() -> None:
    args = parse_args()

    stdin_mode = args.template == '-'

    if stdin_mode:
        # --- Modo stdin ---
        # Resolve o diretório de templates (cwd como fallback)
        if args.templates_dir:
            templates_dir = os.path.abspath(args.templates_dir)
            if not os.path.isdir(templates_dir):
                sys.exit(f"Erro: diretório de templates não encontrado: {templates_dir!r}")
            file_loader = DottedLoader(templates_dir)
        else:
            file_loader = DottedLoader(os.getcwd())

        stdin_content = sys.stdin.read()
        _STDIN_KEY = '__stdin__'

        env = Environment(
            loader=ChoiceLoader([DictLoader({_STDIN_KEY: stdin_content}), file_loader]),
            block_start_string=args.block_start,
            block_end_string=args.block_end,
            variable_start_string=args.variable_start,
            variable_end_string=args.variable_end,
            comment_start_string=args.comment_start,
            comment_end_string=args.comment_end,
            keep_trailing_newline=True,
        )
        env.globals.update({"nid": Cortex.get_next_number})

        try:
            template = env.get_template(_STDIN_KEY)
        except TemplateSyntaxError as exc:
            sys.exit(f"Erro de sintaxe no template stdin (linha {exc.lineno}): {exc.message}")

        context = build_context(args.vars, args.vars_file)

        try:
            rendered = template.render(**context)
        except TemplateNotFound as exc:
            msg = f"Erro: template não encontrado: {exc.name!r}."
            if not args.templates_dir:
                msg += " Dica: use -d para especificar o diretório de templates."
            sys.exit(msg)
        except Exception as exc:  # noqa: BLE001
            sys.exit(f"Erro durante a renderização: {exc}")

    else:
        # --- Modo arquivo (comportamento original) ---
        if args.templates_dir:
            templates_dir = os.path.abspath(args.templates_dir)
        else:
            templates_dir = os.path.abspath(os.path.dirname(args.template) or ".")

        if not os.path.isdir(templates_dir):
            sys.exit(f"Erro: diretório de templates não encontrado: {templates_dir!r}")

        template_name = resolve_template_name(args.template, templates_dir)

        env = Environment(
            loader=DottedLoader(templates_dir),
            block_start_string=args.block_start,
            block_end_string=args.block_end,
            variable_start_string=args.variable_start,
            variable_end_string=args.variable_end,
            comment_start_string=args.comment_start,
            comment_end_string=args.comment_end,
            keep_trailing_newline=True,
        )
        env.globals.update({"nid": Cortex.get_next_number})

        try:
            template = env.get_template(template_name)
        except TemplateNotFound:
            sys.exit(f"Erro: template não encontrado: {template_name!r} em {templates_dir!r}")
        except TemplateSyntaxError as exc:
            sys.exit(f"Erro de sintaxe no template {template_name!r} (linha {exc.lineno}): {exc.message}")

        context = build_context(args.vars, args.vars_file)

        try:
            rendered = template.render(**context)
        except Exception as exc:  # noqa: BLE001
            sys.exit(f"Erro durante a renderização: {exc}")

    sys.stdout.write(rendered)


if __name__ == "__main__":
    main()
