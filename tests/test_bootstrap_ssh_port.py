"""Extração da porta SSH no bootstrap-vps.sh (passo do firewall).

Regressão: `sshd -T | awk '... exit'` sob `set -euo pipefail` pode abortar o bootstrap com rc 141
(SIGPIPE no sshd -T), sem mensagem. O teste extrai a linha real do script e a executa com um
`sshd` falso, sem tocar em SSH, UFW ou na VPS.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prod" / "bootstrap-vps.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None or shutil.which("awk") is None,
                                reason="bash/awk indisponíveis")


def _extract_block() -> str:
    """Linhas da atribuição de SSHP (inclui o padrão 22), exatamente como estão no script."""
    text = SCRIPT.read_text(encoding="utf-8")
    m = re.search(r'^[ \t]*SSHP="\$\(sshd -T.*?\)"\n[ \t]*SSHP="\$\{SSHP:-22\}"[ \t]*$', text, re.M | re.S)
    assert m, "atribuição de SSHP não encontrada em bootstrap-vps.sh"
    return m.group(0)


def _run(fake_sshd: str) -> subprocess.CompletedProcess:
    prog = (
        "set -euo pipefail\n"
        f"sshd() {{ {fake_sshd}; }}\n"
        f"{_extract_block()}\n"
        'echo "PORTA=$SSHP"\n'
    )
    return subprocess.run(["bash", "-c", prog], capture_output=True, text=True, timeout=60)


# Saída grande depois da linha "port": o pipe enche e, com `exit` no awk, o sshd receberia SIGPIPE.
BIG = "head -c 400000 /dev/zero | tr '\\0' 'a'; echo"


def test_script_sem_exit_no_awk_e_com_sintaxe_valida():
    block = _extract_block()
    assert "exit" not in block.split("|")[1], "awk não pode encerrar antes de ler toda a saída"
    assert subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True).returncode == 0


def test_porta_customizada_com_saida_grande_nao_aborta():
    p = _run(f'echo "port 2222"; echo "addressfamily any"; {BIG}')
    assert p.returncode == 0, p.stderr
    assert "PORTA=2222" in p.stdout


def test_usa_a_primeira_porta_quando_ha_varias():
    p = _run('echo "port 2200"; echo "port 2201"')
    assert p.returncode == 0, p.stderr
    assert "PORTA=2200" in p.stdout


def test_sem_linha_port_usa_22():
    p = _run('echo "addressfamily any"')
    assert p.returncode == 0, p.stderr
    assert "PORTA=22" in p.stdout


def test_sshd_falhando_ou_ausente_usa_22():
    assert "PORTA=22" in _run("return 255").stdout
    assert "PORTA=22" in _run("nao_existe_este_comando").stdout


def test_implementacao_antiga_e_a_causa_do_rc_141():
    """Caracteriza a falha original (informativo): com `exit` e saída grande, o pipeline retorna != 0."""
    prog = (
        "set -o pipefail\n"
        f"sshd() {{ echo 'port 2222'; {BIG}; }}\n"
        "sshd | awk '/^port /{print $2; exit}' >/dev/null\n"
        "echo rc=$?\n"
    )
    out = subprocess.run(["bash", "-c", prog], capture_output=True, text=True, timeout=60).stdout
    if "rc=0" in out:  # pragma: no cover - dependente de agendamento do SO
        pytest.skip("SIGPIPE não reproduzido neste ambiente (corrida de pipe)")
    assert re.search(r"rc=(141|1\d\d)", out)
