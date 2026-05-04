"""
Testes unitários U-01, U-02, U-03 — macros utilitárias de genjin.jinja2

  U-01  filter_list_objects
  U-02  is_list
  U-03  is_dict
"""
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).parent / "templates"


# ---------------------------------------------------------------------------
# U-01 — filter_list_objects
# ---------------------------------------------------------------------------

class TestFilterListObjects:
    def test_empty_list(self, run_genjin):
        out = run_genjin(TEMPLATES / "u01_filter_list_objects.jinja2")
        assert "EMPTY_LIST:0" in out

    def test_found_two_matches(self, run_genjin):
        out = run_genjin(TEMPLATES / "u01_filter_list_objects.jinja2")
        assert "FOUND:2" in out

    def test_not_found(self, run_genjin):
        out = run_genjin(TEMPLATES / "u01_filter_list_objects.jinja2")
        assert "NOT_FOUND:0" in out

    def test_attribute_of_attribute(self, run_genjin):
        out = run_genjin(TEMPLATES / "u01_filter_list_objects.jinja2")
        assert "NESTED_FOUND:2" in out


# ---------------------------------------------------------------------------
# U-02 — is_list
# ---------------------------------------------------------------------------

class TestIsList:
    def test_list_returns_true(self, run_genjin):
        out = run_genjin(TEMPLATES / "u02_is_list.jinja2")
        assert "LIST:True" in out

    def test_string_returns_false(self, run_genjin):
        out = run_genjin(TEMPLATES / "u02_is_list.jinja2")
        assert "STRING:False" in out

    def test_dict_returns_false(self, run_genjin):
        out = run_genjin(TEMPLATES / "u02_is_list.jinja2")
        assert "DICT:False" in out

    def test_number_returns_false(self, run_genjin):
        out = run_genjin(TEMPLATES / "u02_is_list.jinja2")
        assert "NUMBER:False" in out

    def test_empty_list_returns_true(self, run_genjin):
        out = run_genjin(TEMPLATES / "u02_is_list.jinja2")
        assert "EMPTY_LIST:True" in out


# ---------------------------------------------------------------------------
# U-03 — is_dict
# ---------------------------------------------------------------------------

class TestIsDict:
    def test_dict_returns_true(self, run_genjin):
        out = run_genjin(TEMPLATES / "u03_is_dict.jinja2")
        assert "DICT:True" in out

    def test_list_returns_false(self, run_genjin):
        out = run_genjin(TEMPLATES / "u03_is_dict.jinja2")
        assert "LIST:False" in out

    def test_string_returns_false(self, run_genjin):
        out = run_genjin(TEMPLATES / "u03_is_dict.jinja2")
        assert "STRING:False" in out

    def test_empty_dict_returns_true(self, run_genjin):
        out = run_genjin(TEMPLATES / "u03_is_dict.jinja2")
        assert "EMPTY_DICT:True" in out
