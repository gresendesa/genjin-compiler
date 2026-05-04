"""
conftest.py — Suite de testes para code/genjin.jinja2

Fixtures compartilhadas entre testes unitários e de integração.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent


def normalize_ids(text: str) -> str:
    """Substitui sufixos hexadecimais de variáveis (6 chars) por XXXXXX.

    Ex.: '#resultAbc123' → '#resultXXXXXX'
    Necessário porque Cortex gera IDs aleatórios a cada execução.
    """
    return re.sub(r'[0-9a-f]{6}', 'XXXXXX', text)


def normalize_output(text: str) -> str:
    """Normaliza IDs e whitespace para comparação estável."""
    normalized = normalize_ids(text)
    lines = [line.strip() for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line)


@pytest.fixture
def run_genjin():
    """Executa um template Jinja2 via assembler.py (stdin) com -d code/.

    Uso:
        output = run_genjin(template_path)          # positivo
        stderr = run_genjin(template_path, expect_error=True)  # negativo

    Retorna stdout (positivo) ou stderr (negativo).
    """
    def _run(template_path: Path, expect_error: bool = False) -> str:
        content = Path(template_path).read_text(encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "assembler.py", "-", "-d", "code/"],
            input=content,
            capture_output=True,
            text=True,
            cwd=str(REPO),
        )
        if expect_error:
            assert result.returncode != 0, (
                f"Esperado erro, mas assembler retornou sucesso.\nstdout:\n{result.stdout}"
            )
            return result.stderr
        else:
            assert result.returncode == 0, (
                f"Esperado sucesso, mas assembler retornou erro.\nstderr:\n{result.stderr}"
            )
            return result.stdout

    return _run
