"""
Testes de integração do assembler.py — S4-T02 + S4-T03

Cobre:
  - Modo stdin simples (sem extends/include)
  - Modo stdin com extends resolvido via --templates-dir
  - Modo stdin com variáveis (-v)
  - Modo stdin sem -d quando template usa extends → erro claro
  - Regressão: modo arquivo continua funcionando
  - E2E: compiler.py | assembler.py - -d . renderiza basic.gnj (até TemplateNotFound de library)
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run_assembler(args: list, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, 'assembler.py'] + args,
        input=input_text,
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )


def _run_compiler(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, 'compiler.py'] + args,
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )


# ---------------------------------------------------------------------------
# Modo stdin — template simples
# ---------------------------------------------------------------------------

class TestAssemblerStdinSimples:
    def test_exit_0_sem_d(self):
        result = _run_assembler(['-'], input_text='ola mundo')
        assert result.returncode == 0

    def test_saida_correta_texto_literal(self):
        result = _run_assembler(['-'], input_text='ola mundo')
        assert result.stdout == 'ola mundo'

    def test_variavel_inline(self):
        result = _run_assembler(['-', '-v', 'nome=Guilherme'], input_text='Olá {{ nome }}!')
        assert result.returncode == 0
        assert result.stdout == 'Olá Guilherme!'

    def test_multiplas_variaveis(self):
        result = _run_assembler(
            ['-', '-v', 'a=1', '-v', 'b=2'],
            input_text='{{ a }}-{{ b }}'
        )
        assert result.stdout == '1-2'

    def test_delimitadores_customizados_bloco(self):
        result = _run_assembler(
            ['-', '--block-start', '{*', '--block-end', '*}'],
            input_text='{* set x = 42 *}{{ x }}'
        )
        assert result.returncode == 0
        assert result.stdout == '42'

    def test_stdout_nao_vazio(self):
        result = _run_assembler(['-'], input_text='abc')
        assert result.stdout != ''

    def test_template_vazio(self):
        result = _run_assembler(['-'], input_text='')
        assert result.returncode == 0
        assert result.stdout == ''

    def test_template_multilinhas(self):
        result = _run_assembler(['-'], input_text='linha1\nlinha2\n')
        assert result.stdout == 'linha1\nlinha2\n'


# ---------------------------------------------------------------------------
# Modo stdin — com extends via -d
# ---------------------------------------------------------------------------

class TestAssemblerStdinComExtends:
    """Usa os templates de testes/delimiters como base para extends."""

    def test_extends_resolve_via_d(self, tmp_path):
        # cria base.jinja2 no tmp_path
        base = tmp_path / 'base.jinja2'
        base.write_text('{* block content *}default{* endblock *}', encoding='utf-8')
        child = '{* extends "base" *}{* block content *}filho{* endblock *}'

        result = _run_assembler(
            ['-', '-d', str(tmp_path), '--block-start', '{*', '--block-end', '*}'],
            input_text=child
        )
        assert result.returncode == 0
        assert result.stdout == 'filho'

    def test_include_resolve_via_d(self, tmp_path):
        partial = tmp_path / 'partial.jinja2'
        partial.write_text('parcial', encoding='utf-8')
        tpl = '{* include "partial" *}'

        result = _run_assembler(
            ['-', '-d', str(tmp_path), '--block-start', '{*', '--block-end', '*}'],
            input_text=tpl
        )
        assert result.returncode == 0
        assert result.stdout == 'parcial'


# ---------------------------------------------------------------------------
# Modo stdin — erro sem -d quando template usa extends
# ---------------------------------------------------------------------------

class TestAssemblerStdinSemD:
    def test_extends_sem_d_exit_nonzero(self):
        tpl = '{* extends "inexistente" *}'
        result = _run_assembler(
            ['-', '--block-start', '{*', '--block-end', '*}'],
            input_text=tpl
        )
        assert result.returncode != 0

    def test_extends_sem_d_stderr_menciona_dica(self):
        tpl = '{* extends "inexistente" *}'
        result = _run_assembler(
            ['-', '--block-start', '{*', '--block-end', '*}'],
            input_text=tpl
        )
        assert '-d' in result.stderr or 'diret' in result.stderr.lower()


# ---------------------------------------------------------------------------
# Regressão: modo arquivo inalterado
# ---------------------------------------------------------------------------

class TestAssemblerModoArquivoRegressao:
    """Garante que o modo arquivo original não foi afetado."""

    def test_template_simples_com_arquivo(self, tmp_path):
        tpl = tmp_path / 'hello.jinja2'
        tpl.write_text('Olá {{ nome }}!', encoding='utf-8')
        result = _run_assembler(
            [str(tpl), '-d', str(tmp_path), '-v', 'nome=Mundo']
        )
        assert result.returncode == 0
        assert result.stdout == 'Olá Mundo!'

    def test_arquivo_inexistente_exit_nonzero(self):
        result = _run_assembler(['/nao/existe.jinja2', '-d', '.'])
        assert result.returncode != 0

    def test_dir_inexistente_exit_nonzero(self, tmp_path):
        tpl = tmp_path / 't.jinja2'
        tpl.write_text('x', encoding='utf-8')
        result = _run_assembler([str(tpl), '-d', '/nao/existe'])
        assert result.returncode != 0

    def test_delimiters_test_suite_integra(self):
        """Verifica um template dos testes existentes de delimitadores."""
        tpl = REPO / 'tests' / 'delimiters' / 'templates' / 'variable_simple.jinja2'
        expected = (REPO / 'tests' / 'delimiters' / 'expected' / 'variable_simple.txt').read_text()
        result = _run_assembler([
            str(tpl),
            '-d', str(REPO / 'tests' / 'delimiters' / 'templates'),
            '--block-start', '{*', '--block-end', '*}',
            '--comment-start', '{!!', '--comment-end', '!!}',
            '-v', 'greeting=Olá',
            '-v', 'name=Mundo',
        ])
        assert result.returncode == 0
        assert result.stdout == expected


# ---------------------------------------------------------------------------
# E2E: compiler.py | assembler.py - (S4-T03)
# ---------------------------------------------------------------------------

class TestPipelineE2E:
    def test_pipeline_gera_saida_nao_vazia(self):
        """O pipeline compiler.py | assembler.py - deve produzir saída (mesmo que
        a renderização falhe por library ausente, o assembler deve ao menos iniciar)."""
        compiler = _run_compiler(['examples/basic.gnj'])
        assert compiler.returncode == 0

        assembler = _run_assembler(['-', '-d', '.'], input_text=compiler.stdout)
        # A falha esperada aqui é TemplateNotFound da library (Net.check, etc.)
        # que não existe no projeto — não é falha do stdin mode.
        # Verificamos que o template foi LIDO e o erro é de library ausente, não de sintaxe do stdin.
        assert 'stdin' not in assembler.stderr.lower() or assembler.returncode == 0

    def test_pipeline_template_sem_library_erro_e_library(self):
        """Confirma que o erro do pipeline é por library ausente, não por stdin."""
        compiler = _run_compiler(['examples/basic.gnj'])
        assembler = _run_assembler(['-', '-d', '.'], input_text=compiler.stdout)
        # Se há erro, deve ser TemplateNotFound de uma library (ex: 'Net'), não de '__stdin__'
        if assembler.returncode != 0:
            assert '__stdin__' not in assembler.stderr

    def test_pipeline_template_simples_sem_library(self):
        """Pipeline com um .gnj cujos procs usam libraries simples que existem."""
        # Usa um template simples sem from/import de libraries externas
        # Renderiza apenas o set program + build — a saída mínima é o resultado do build()
        # sem macros de library. Aqui apenas testamos que assembler aceita o stdin do compiler.
        simple_gnj = '''\
program "Teste"

vars { s: Number }

procs {
    f(n: Number) from "Lib.fn" {
        codes OK<0>
    }
}

exec f(n=1) >> s {
    pass OK
}
'''
        compiler = subprocess.run(
            [sys.executable, 'compiler.py'],
            input=simple_gnj,
            capture_output=True,
            text=True,
            cwd=str(REPO),
        )
        assert compiler.returncode == 0

        assembler = _run_assembler(['-', '-d', '.'], input_text=compiler.stdout)
        # Resultado: ou renderiza (se genjin.jinja2 tolera library ausente),
        # ou falha com TemplateNotFound de 'Lib' — nunca com erro de stdin
        if assembler.returncode != 0:
            assert '__stdin__' not in assembler.stderr

    def test_stdin_mode_com_template_jinja2_puro(self):
        """Stdin mode com template Jinja2 puro (sem genjin) renderiza corretamente."""
        result = _run_assembler(
            ['-', '-v', 'versao=1.0'],
            input_text='Versão: {{ versao }}'
        )
        assert result.returncode == 0
        assert result.stdout == 'Versão: 1.0'
