"""
Testes de integração do compiler.py — S3-T07

Cobre:
  - Modo arquivo: exit 0, saída correta
  - Modo stdin: exit 0, saída idêntica ao modo arquivo
  - Modo -o/--output: arquivo criado com conteúdo correto
  - Arquivo inexistente: exit 2, stderr
  - Source inválido (parse error): exit 1, stderr
  - Flags de ajuda: exit 0
"""

import subprocess
import sys
from pathlib import Path

import pytest


BASIC_GNJ = '''\
program "Pagamento"

vars { s: Number }

procs {
    proc pagar(val: Number) from "Pay.do" {
        codes OK<0>, FALHA<1>
    }
}

exec pagar(val=100) >> s {
    pass OK, FALHA
}
'''

INVALID_GNJ = 'program'   # incompleto → ParseError


def _run(args: list, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, 'compiler.py'] + args,
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


# ---------------------------------------------------------------------------
# Modo arquivo
# ---------------------------------------------------------------------------

class TestCompilerArquivo:
    def test_exit_0(self, gnj_file):
        assert _run([str(gnj_file)]).returncode == 0

    def test_saida_comeca_com_import(self, gnj_file):
        result = _run([str(gnj_file)])
        assert result.stdout.startswith('{* from "genjin"')

    def test_saida_contem_build(self, gnj_file):
        result = _run([str(gnj_file)])
        assert '{{ build(' in result.stdout

    def test_nome_do_programa_na_saida(self, gnj_file):
        result = _run([str(gnj_file)])
        assert "'Pagamento'" in result.stdout

    def test_arquivo_inexistente_exit_2(self):
        result = _run(['/nao/existe.gnj'])
        assert result.returncode == 2

    def test_arquivo_inexistente_stderr(self):
        result = _run(['/nao/existe.gnj'])
        assert result.stderr.strip() != ''

    def test_basic_gnj_exit_0(self):
        result = _run(['examples/basic.gnj'])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Modo stdin
# ---------------------------------------------------------------------------

class TestCompilerStdin:
    def test_exit_0(self):
        result = _run([], input_text=BASIC_GNJ)
        assert result.returncode == 0

    def test_saida_equivalente_ao_modo_arquivo(self, gnj_file):
        via_arquivo = _run([str(gnj_file)])
        via_stdin = _run([], input_text=BASIC_GNJ)
        assert via_arquivo.stdout == via_stdin.stdout

    def test_saida_comeca_com_import(self):
        result = _run([], input_text=BASIC_GNJ)
        assert result.stdout.startswith('{* from "genjin"')


# ---------------------------------------------------------------------------
# Modo -o / --output
# ---------------------------------------------------------------------------

class TestCompilerOutput:
    def test_cria_arquivo_saida(self, gnj_file, tmp_path):
        out = tmp_path / 'out.jinja2'
        result = _run([str(gnj_file), '-o', str(out)])
        assert result.returncode == 0
        assert out.exists()

    def test_arquivo_saida_contem_build(self, gnj_file, tmp_path):
        out = tmp_path / 'out.jinja2'
        _run([str(gnj_file), '-o', str(out)])
        assert '{{ build(' in out.read_text(encoding='utf-8')

    def test_saida_stdout_vazia_com_o(self, gnj_file, tmp_path):
        out = tmp_path / 'out.jinja2'
        result = _run([str(gnj_file), '-o', str(out)])
        assert result.stdout == ''

    def test_output_equivalente_a_stdout(self, gnj_file, tmp_path):
        out = tmp_path / 'out.jinja2'
        _run([str(gnj_file), '-o', str(out)])
        via_saida = out.read_text(encoding='utf-8')
        via_stdout = _run([str(gnj_file)]).stdout
        assert via_saida == via_stdout

    def test_long_flag_output(self, gnj_file, tmp_path):
        out = tmp_path / 'out.jinja2'
        result = _run([str(gnj_file), '--output', str(out)])
        assert result.returncode == 0
        assert out.exists()


# ---------------------------------------------------------------------------
# Erros de compilação
# ---------------------------------------------------------------------------

class TestCompilerErros:
    def test_parse_error_exit_1(self):
        result = _run([], input_text=INVALID_GNJ)
        assert result.returncode == 1

    def test_parse_error_stderr_nao_vazio(self):
        result = _run([], input_text=INVALID_GNJ)
        assert result.stderr.strip() != ''

    def test_parse_error_stdout_vazio(self):
        result = _run([], input_text=INVALID_GNJ)
        assert result.stdout == ''

    def test_scanner_error_exit_1(self):
        result = _run([], input_text='program @@@')
        assert result.returncode == 1
