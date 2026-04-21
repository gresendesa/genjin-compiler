"""
Testes de conformidade dos delimitadores customizados do projeto GenJin.

Delimitadores testados (conforme example.sh):
  Blocos    : {* ... *}
  Variáveis : {{ ... }}
  Comentários: {!! ... !!}

Cada teste renderiza um template de tests/delimiters/templates/ e compara
o resultado byte a byte com o arquivo em tests/delimiters/expected/.
"""

import os
import pytest

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
EXPECTED_DIR  = os.path.join(os.path.dirname(__file__), "expected")


def expected(filename: str) -> str:
    with open(os.path.join(EXPECTED_DIR, filename), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Delimitadores de bloco  {* ... *}
# ---------------------------------------------------------------------------

class TestBlockDelimiters:
    """Verifica que {* *} é reconhecido como delimitador de bloco."""

    def test_set_e_if(self, make_env):
        """set + if/else/endif devem ser avaliados corretamente."""
        result = make_env(TEMPLATES_DIR).get_template("block_set_if.jinja2").render()
        assert result == expected("block_set_if.txt")

    def test_for(self, make_env):
        """Laço for/endfor deve iterar e produzir saída concatenada."""
        result = make_env(TEMPLATES_DIR).get_template("block_for.jinja2").render()
        assert result == expected("block_for.txt")

    def test_macro(self, make_env):
        """macro/endmacro deve definir e permitir chamar a macro via variável."""
        result = make_env(TEMPLATES_DIR).get_template("block_macro.jinja2").render()
        assert result == expected("block_macro.txt")


# ---------------------------------------------------------------------------
# Delimitadores de variável  {{ ... }}
# ---------------------------------------------------------------------------

class TestVariableDelimiters:
    """Verifica que {{ }} interpola variáveis e expressões corretamente."""

    def test_variaveis_simples(self, make_env):
        """Duas variáveis de contexto devem ser interpoladas na saída."""
        result = make_env(TEMPLATES_DIR).get_template("variable_simple.jinja2").render(
            greeting="Olá", name="Mundo"
        )
        assert result == expected("variable_simple.txt")

    def test_expressao_aritmetica(self, make_env):
        """Expressão aritmética dentro de {{ }} deve ser avaliada."""
        result = make_env(TEMPLATES_DIR).get_template("variable_expression.jinja2").render(value=6)
        assert result == expected("variable_expression.txt")


# ---------------------------------------------------------------------------
# Delimitadores de comentário  {!! ... !!}
# ---------------------------------------------------------------------------

class TestCommentDelimiters:
    """Verifica que {!! !!} suprime o conteúdo comentado da saída."""

    def test_comentario_inline(self, make_env):
        """Comentário em linha não deve aparecer na saída."""
        result = make_env(TEMPLATES_DIR).get_template("comment_inline.jinja2").render()
        assert result == expected("comment_inline.txt")
        assert "deve desaparecer" not in result

    def test_comentario_multilinhas(self, make_env):
        """Comentário em bloco multilinhas não deve aparecer na saída."""
        result = make_env(TEMPLATES_DIR).get_template("comment_block.jinja2").render()
        assert result == expected("comment_block.txt")
        assert "deve desaparecer" not in result


# ---------------------------------------------------------------------------
# Composição de templates  (include / extends)
# ---------------------------------------------------------------------------

class TestTemplateComposition:
    """Verifica que include e extends funcionam com os delimitadores customizados."""

    def test_include(self, make_env):
        """include deve inserir o conteúdo do parcial na saída."""
        result = make_env(TEMPLATES_DIR).get_template("composition_include.jinja2").render()
        assert "PARCIAL_OK" in result

    def test_extends(self, make_env):
        """extends deve herdar o layout base e sobrescrever o bloco filho."""
        result = make_env(TEMPLATES_DIR).get_template("composition_child.jinja2").render()
        assert result == expected("composition_extends.txt")
