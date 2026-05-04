"""
Testes de integração I-01, I-05, I-08 — pipeline completo com genjin.jinja2

  I-01  Pipeline mínimo: 1 proc sem params, 1 output code, sem cases
  I-05  Bloco com LOOP_WHILE → DO/WHILE gerado
  I-08  Sentinel EXP-005: código borbulhado absorvido por LOOP_WHILE intermediário
"""
import re
from pathlib import Path

TEMPLATES = Path(__file__).parent / "templates"


def normalize_ids(text: str) -> str:
    return re.sub(r'[0-9a-f]{6}', 'XXXXXX', text)


# ---------------------------------------------------------------------------
# I-01 — Pipeline mínimo
# ---------------------------------------------------------------------------

class TestMinimalPipeline:
    def test_compiles_without_error(self, run_genjin):
        """Template mínimo deve compilar sem erro."""
        run_genjin(TEMPLATES / "i01_minimal.jinja2")

    def test_call_noop_present_in_output(self, run_genjin):
        """Saída deve conter a chamada ao proc 'noop_proc'."""
        out = run_genjin(TEMPLATES / "i01_minimal.jinja2")
        assert "CALL_NOOP(" in out

    def test_variable_reference_present_in_output(self, run_genjin):
        """Saída deve conter referência à variável #result com ID hexadecimal."""
        out = run_genjin(TEMPLATES / "i01_minimal.jinja2")
        assert re.search(r"#result[0-9a-f]{6}", out)

    def test_no_loop_in_output(self, run_genjin):
        """Sem LOOP_WHILE: não deve gerar DO;/WHILE; na saída."""
        out = run_genjin(TEMPLATES / "i01_minimal.jinja2")
        assert "DO;" not in out
        assert "WHILE(" not in out


# ---------------------------------------------------------------------------
# I-05 — LOOP_WHILE → DO/WHILE
# ---------------------------------------------------------------------------

class TestLoopWhile:
    def test_compiles_without_error(self, run_genjin):
        run_genjin(TEMPLATES / "i05_loop_while.jinja2")

    def test_do_while_structure_present(self, run_genjin):
        """LOOP_WHILE deve gerar estrutura DO; ... WHILE(...);"""
        out = run_genjin(TEMPLATES / "i05_loop_while.jinja2")
        assert "DO;" in out
        assert "WHILE(" in out

    def test_fetch_call_inside_loop(self, run_genjin):
        """Chamada ao proc deve estar entre DO; e WHILE(;."""
        out = run_genjin(TEMPLATES / "i05_loop_while.jinja2")
        do_pos = out.find("DO;")
        fetch_pos = out.find("FETCH(")
        while_pos = out.find("WHILE(")
        assert do_pos < fetch_pos < while_pos

    def test_while_condition_uses_retry_code(self, run_genjin):
        """Condição do WHILE deve usar o código numérico de RETRY (1)."""
        out = normalize_ids(run_genjin(TEMPLATES / "i05_loop_while.jinja2"))
        assert "WHILE(#statusXXXXXX==1)" in out


# ---------------------------------------------------------------------------
# I-08 — Sentinel EXP-005
# ---------------------------------------------------------------------------

class TestExp005Sentinel:
    def test_compiles_without_error(self, run_genjin):
        """Sentinel EXP-005: estrutura baz(LOOP_WHILE)→bar(DEMORA) deve compilar sem erro.

        Sem o fix de SPR-2026-15 este teste levantaria uma exceção:
          "The codes ['DEMORA'] ... must be handled locally..."
        """
        run_genjin(TEMPLATES / "i08_exp005_sentinel.jinja2")

    def test_doe_proc_called(self, run_genjin):
        """Proc doe deve ser chamado na saída."""
        out = run_genjin(TEMPLATES / "i08_exp005_sentinel.jinja2")
        assert "DOE(" in out

    def test_baz_proc_called(self, run_genjin):
        """Proc baz deve ser chamado (dentro do CASE OK de doe)."""
        out = run_genjin(TEMPLATES / "i08_exp005_sentinel.jinja2")
        assert "BAZ(" in out

    def test_bar_proc_called(self, run_genjin):
        """Proc bar deve ser chamado (dentro do CASE OK de baz)."""
        out = run_genjin(TEMPLATES / "i08_exp005_sentinel.jinja2")
        assert "BAR(" in out
