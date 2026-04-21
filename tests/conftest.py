import pytest
from jinja2 import Environment, FileSystemLoader

# Delimitadores usados pelo projeto (espelhados do example.sh)
PROJECT_DELIMITERS = {
    "block_start_string": "{*",
    "block_end_string": "*}",
    "variable_start_string": "{{",
    "variable_end_string": "}}",
    "comment_start_string": "{!!",
    "comment_end_string": "!!}",
}


@pytest.fixture
def make_env():
    """Retorna uma factory que cria um Environment Jinja2 com os delimitadores do projeto."""
    def _make(templates_dir: str, **overrides):
        params = {**PROJECT_DELIMITERS, **overrides}
        return Environment(
            loader=FileSystemLoader(str(templates_dir)),
            keep_trailing_newline=True,
            **params,
        )
    return _make
