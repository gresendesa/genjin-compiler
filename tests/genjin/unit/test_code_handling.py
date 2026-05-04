"""
Testes unitários U-10, U-11 — macros de validação de códigos de genjin.jinja2

  U-10  get_unhandled_codes
  U-11  get_unhandled_codes_recursively (inclui sentinel EXP-005)
"""
from pathlib import Path

TEMPLATES = Path(__file__).parent / "templates"


# ---------------------------------------------------------------------------
# U-10 — get_unhandled_codes
# ---------------------------------------------------------------------------

class TestGetUnhandledCodes:
    def test_no_cases_no_while_all_unhandled(self, run_genjin):
        out = run_genjin(TEMPLATES / "u10_get_unhandled_codes.jinja2")
        # Todos os 3 códigos do proc (DEMORA,ERROR,OK) devem aparecer
        assert "NO_HANDLING:DEMORA,ERROR,OK" in out

    def test_case_covers_ok(self, run_genjin):
        out = run_genjin(TEMPLATES / "u10_get_unhandled_codes.jinja2")
        # OK tratado por CASE; restam DEMORA e ERROR
        assert "CASE_COVERS_OK:DEMORA,ERROR" in out

    def test_while_covers_error_and_demora(self, run_genjin):
        out = run_genjin(TEMPLATES / "u10_get_unhandled_codes.jinja2")
        # ERROR e DEMORA tratados por LOOP_WHILE; resta apenas OK
        assert "WHILE_COVERS_ERROR_DEMORA:OK" in out

    def test_all_covered_returns_empty(self, run_genjin):
        out = run_genjin(TEMPLATES / "u10_get_unhandled_codes.jinja2")
        # CASE + WHILE cobrem tudo
        assert "ALL_COVERED:0" in out


# ---------------------------------------------------------------------------
# U-11 — get_unhandled_codes_recursively
# ---------------------------------------------------------------------------

class TestGetUnhandledCodesRecursively:
    # ── Sentinel EXP-005 ──────────────────────────────────────────────────
    def test_exp005_demora_not_bubbled(self, run_genjin):
        """DEMORA não deve ultrapassar o baz que tem LOOP_WHILE=['ERROR','DEMORA']."""
        out = run_genjin(TEMPLATES / "u11_get_unhandled_codes_recursively.jinja2")
        assert "EXP005_DEMORA_IN_DICT:False" in out

    def test_exp005_error_not_bubbled(self, run_genjin):
        """ERROR também deve ser absorvido pelo LOOP_WHILE de baz."""
        out = run_genjin(TEMPLATES / "u11_get_unhandled_codes_recursively.jinja2")
        assert "EXP005_ERROR_IN_DICT:False" in out

    def test_exp005_ok_bubbles_through(self, run_genjin):
        """OK não está em LOOP_WHILE de baz, logo deve borbulhar."""
        out = run_genjin(TEMPLATES / "u11_get_unhandled_codes_recursively.jinja2")
        assert "EXP005_OK_IN_DICT:True" in out

    # ── Bloco folha (sem CASES) ───────────────────────────────────────────
    def test_leaf_block_all_codes_unhandled(self, run_genjin):
        """Bloco folha sem CASES nem LOOP_WHILE borbulha todos os códigos."""
        out = run_genjin(TEMPLATES / "u11_get_unhandled_codes_recursively.jinja2")
        assert "LEAF_UNHANDLED:FAIL,OK" in out
