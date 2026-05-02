"""
Testes dos CLIs do compilador Genjin — S3-T05

Cobre:
  - compiler.scanner: arquivo, stdin, erro de arquivo, erro de sintaxe, exit codes
  - compiler.parser: stdin de tokens, --source, erro de arquivo, erro de parse, exit codes
  - compiler.transpiler: stdin de AST, --source, erro de arquivo, exit codes
  - Pipeline completo scanner | parser | transpiler via subprocess
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASIC_GNJ = '''\
program "T"

vars {
    s: Number
    r: Text
}

procs {
    f(n: Number, res: &Text) from "A.b" {
        codes OK<0>, ERR<1>
    }
}

exec f(n=42, res=&r) >> s {
    pass OK, ERR
}
'''

INVALID_GNJ = 'program'   # source incompleto → ParseError


def _run(args: list, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, '-m'] + args,
        input=input_text,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
    )


@pytest.fixture
def gnj_file(tmp_path):
    f = tmp_path / 'prog.gnj'
    f.write_text(BASIC_GNJ, encoding='utf-8')
    return f


@pytest.fixture
def invalid_gnj_file(tmp_path):
    f = tmp_path / 'bad.gnj'
    f.write_text(INVALID_GNJ, encoding='utf-8')
    return f


# ---------------------------------------------------------------------------
# compiler.scanner
# ---------------------------------------------------------------------------

class TestScannerCLI:
    def test_arquivo_exit_0(self, gnj_file):
        result = _run(['compiler.scanner', str(gnj_file)])
        assert result.returncode == 0

    def test_arquivo_saida_e_json_valido(self, gnj_file):
        result = _run(['compiler.scanner', str(gnj_file)])
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_arquivo_tokens_tem_type_value_line(self, gnj_file):
        result = _run(['compiler.scanner', str(gnj_file)])
        tokens = json.loads(result.stdout)
        for tok in tokens:
            assert 'type' in tok and 'value' in tok and 'line' in tok

    def test_arquivo_primeiro_token_kw_program(self, gnj_file):
        result = _run(['compiler.scanner', str(gnj_file)])
        tokens = json.loads(result.stdout)
        assert tokens[0]['type'] == 'KW_PROGRAM'

    def test_stdin_exit_0(self):
        result = _run(['compiler.scanner'], input_text=BASIC_GNJ)
        assert result.returncode == 0

    def test_stdin_saida_equivalente_a_arquivo(self, gnj_file):
        via_arquivo = _run(['compiler.scanner', str(gnj_file)])
        via_stdin = _run(['compiler.scanner'], input_text=BASIC_GNJ)
        assert json.loads(via_arquivo.stdout) == json.loads(via_stdin.stdout)

    def test_arquivo_inexistente_exit_2(self):
        result = _run(['compiler.scanner', '/nao/existe.gnj'])
        assert result.returncode == 2

    def test_arquivo_inexistente_stderr(self):
        result = _run(['compiler.scanner', '/nao/existe.gnj'])
        assert result.stderr.strip() != ''

    def test_syntax_error_exit_1(self):
        result = _run(['compiler.scanner'], input_text='program ###')
        assert result.returncode == 1

    def test_syntax_error_stderr_mensagem(self):
        result = _run(['compiler.scanner'], input_text='program ###')
        assert result.stderr.strip() != ''

    def test_muitos_args_exit_2(self, gnj_file):
        result = _run(['compiler.scanner', str(gnj_file), 'extra'])
        assert result.returncode == 2

    def test_eof_token_presente(self, gnj_file):
        result = _run(['compiler.scanner', str(gnj_file)])
        tokens = json.loads(result.stdout)
        assert tokens[-1]['type'] == 'EOF'


# ---------------------------------------------------------------------------
# compiler.parser
# ---------------------------------------------------------------------------

class TestParserCLI:
    def _tokens_json(self) -> str:
        result = _run(['compiler.scanner'], input_text=BASIC_GNJ)
        return result.stdout

    def test_stdin_exit_0(self):
        result = _run(['compiler.parser'], input_text=self._tokens_json())
        assert result.returncode == 0

    def test_stdin_saida_json_valido(self):
        result = _run(['compiler.parser'], input_text=self._tokens_json())
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_stdin_raiz_e_program_node(self):
        result = _run(['compiler.parser'], input_text=self._tokens_json())
        data = json.loads(result.stdout)
        assert data['__type__'] == 'ProgramNode'

    def test_stdin_nome_do_programa(self):
        result = _run(['compiler.parser'], input_text=self._tokens_json())
        data = json.loads(result.stdout)
        assert data['name'] == 'T'

    def test_source_exit_0(self, gnj_file):
        result = _run(['compiler.parser', '--source', str(gnj_file)])
        assert result.returncode == 0

    def test_source_resultado_equivalente_a_stdin(self, gnj_file):
        via_stdin = _run(['compiler.parser'], input_text=self._tokens_json())
        via_source = _run(['compiler.parser', '--source', str(gnj_file)])
        assert json.loads(via_stdin.stdout) == json.loads(via_source.stdout)

    def test_arquivo_tokens_inexistente_exit_2(self):
        result = _run(['compiler.parser', '/nao/existe.json'])
        assert result.returncode == 2

    def test_source_inexistente_exit_2(self):
        result = _run(['compiler.parser', '--source', '/nao/existe.gnj'])
        assert result.returncode == 2

    def test_parse_error_exit_1(self):
        # tokens de programa inválido
        bad_tokens = _run(['compiler.scanner'], input_text=INVALID_GNJ)
        result = _run(['compiler.parser'], input_text=bad_tokens.stdout)
        assert result.returncode == 1

    def test_parse_error_stderr(self):
        bad_tokens = _run(['compiler.scanner'], input_text=INVALID_GNJ)
        result = _run(['compiler.parser'], input_text=bad_tokens.stdout)
        assert result.stderr.strip() != ''


# ---------------------------------------------------------------------------
# compiler.transpiler
# ---------------------------------------------------------------------------

class TestTranspilerCLI:
    def _ast_json(self) -> str:
        tokens = _run(['compiler.scanner'], input_text=BASIC_GNJ)
        ast = _run(['compiler.parser'], input_text=tokens.stdout)
        return ast.stdout

    def test_stdin_exit_0(self):
        result = _run(['compiler.transpiler'], input_text=self._ast_json())
        assert result.returncode == 0

    def test_stdin_saida_comeca_com_import(self):
        result = _run(['compiler.transpiler'], input_text=self._ast_json())
        assert result.stdout.startswith('{* from "genjin"')

    def test_stdin_saida_contem_build(self):
        result = _run(['compiler.transpiler'], input_text=self._ast_json())
        assert '{{ build(' in result.stdout

    def test_source_exit_0(self, gnj_file):
        result = _run(['compiler.transpiler', '--source', str(gnj_file)])
        assert result.returncode == 0

    def test_source_resultado_equivalente_a_stdin(self, gnj_file):
        via_stdin = _run(['compiler.transpiler'], input_text=self._ast_json())
        via_source = _run(['compiler.transpiler', '--source', str(gnj_file)])
        assert via_stdin.stdout == via_source.stdout

    def test_arquivo_ast_inexistente_exit_2(self):
        result = _run(['compiler.transpiler', '/nao/existe.json'])
        assert result.returncode == 2

    def test_source_inexistente_exit_2(self):
        result = _run(['compiler.transpiler', '--source', '/nao/existe.gnj'])
        assert result.returncode == 2


# ---------------------------------------------------------------------------
# Pipeline completo: scanner | parser | transpiler
# ---------------------------------------------------------------------------

class TestPipelineCLI:
    def test_pipeline_exit_0(self, gnj_file):
        scan = _run(['compiler.scanner', str(gnj_file)])
        assert scan.returncode == 0
        parse = _run(['compiler.parser'], input_text=scan.stdout)
        assert parse.returncode == 0
        transp = _run(['compiler.transpiler'], input_text=parse.stdout)
        assert transp.returncode == 0

    def test_pipeline_saida_equivalente_a_source(self, gnj_file):
        scan = _run(['compiler.scanner', str(gnj_file)])
        parse = _run(['compiler.parser'], input_text=scan.stdout)
        pipeline = _run(['compiler.transpiler'], input_text=parse.stdout)

        direct = _run(['compiler.transpiler', '--source', str(gnj_file)])
        assert pipeline.stdout == direct.stdout

    def test_pipeline_com_basic_gnj(self):
        """Testa com o exemplo canônico examples/basic.gnj."""
        basic = Path(__file__).parent.parent.parent / 'examples' / 'basic.gnj'
        scan = _run(['compiler.scanner', str(basic)])
        assert scan.returncode == 0
        parse = _run(['compiler.parser'], input_text=scan.stdout)
        assert parse.returncode == 0
        transp = _run(['compiler.transpiler'], input_text=parse.stdout)
        assert transp.returncode == 0
        assert '{* from "genjin"' in transp.stdout

    def test_pipeline_nome_programa_na_saida(self, gnj_file):
        scan = _run(['compiler.scanner', str(gnj_file)])
        parse = _run(['compiler.parser'], input_text=scan.stdout)
        transp = _run(['compiler.transpiler'], input_text=parse.stdout)
        assert "'T'" in transp.stdout
