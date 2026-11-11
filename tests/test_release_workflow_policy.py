"""Política do pipeline de release (sem PyYAML: checagens textuais dos workflows).

Garante, a cada CI, que: só TAG vX.Y.Z dispara deploy; push em main roda só o CI; não
há aprovação manual (Environment); o deploy depende de CI+publicação; há concorrência sem
cancelamento; o deploy não constrói na VPS; e a validação de tag aceita/recusa o esperado.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"


def _read(name: str) -> str:
    return (WF / name).read_text(encoding="utf-8")


def _job_block(text: str, job: str) -> str:
    m = re.search(rf"^  {re.escape(job)}:\n(.*?)(?=^  [a-z][a-z0-9_-]*:\n|\Z)", text, re.S | re.M)
    assert m, f"job {job} não encontrado"
    return m.group(1)


def test_somente_workflows_esperados():
    assert sorted(p.name for p in WF.glob("*.yml")) == ["ci.yml", "release.yml"]


def test_release_dispara_somente_em_tag_de_versao():
    text = _read("release.yml")
    on_block = re.search(r"^on:\n(.*?)(?=^\S)", text, re.S | re.M).group(1)
    assert "tags:" in on_block and '"v*.*.*"' in on_block
    assert "branches" not in on_block, "push de branch não pode disparar o release"
    for forbidden in ("workflow_dispatch", "pull_request", "schedule", "workflow_run"):
        assert forbidden not in on_block


def test_ci_roda_em_main_e_pr_mas_nunca_em_tag_e_nunca_implanta():
    text = _read("ci.yml")
    on_block = re.search(r"^on:\n(.*?)(?=^\S)", text, re.S | re.M).group(1)
    assert "branches: [main]" in on_block
    assert "tags" not in on_block
    assert "workflow_call" in on_block
    for forbidden in ("ssh ", "ghcr.io/", "packages: write", "VPS_"):
        assert forbidden not in text, f"ci.yml não pode conter {forbidden!r}"


def test_sem_aprovacao_manual_nenhum_environment():
    for name in ("release.yml", "ci.yml"):
        assert not re.search(r"^\s*environment:", _read(name), re.M), f"{name} usa Environment (aprovação)"


def test_deploy_depende_de_validacao_ci_e_publicacao():
    text = _read("release.yml")
    assert re.search(r"needs: validate-tag\n\s+uses: \./\.github/workflows/ci\.yml", text)
    assert "needs: [validate-tag, ci]" in _job_block(text, "publish")
    assert "needs: [validate-tag, publish]" in _job_block(text, "deploy")


def test_deploy_serializado_e_sem_cancelar():
    deploy = _job_block(_read("release.yml"), "deploy")
    assert "group: deploy-production" in deploy
    assert "cancel-in-progress: false" in deploy


def test_deploy_usa_imagens_publicadas_e_nao_constroi_na_vps():
    deploy = _job_block(_read("release.yml"), "deploy")
    assert "scripts/prod/release.sh" in deploy
    assert "docker build" not in deploy and "compose build" not in deploy
    # imagens por tag exata; nunca latest como referência de deploy
    assert ":latest" not in _read("release.yml")


def test_tag_exige_commit_na_main_e_permissoes_minimas():
    text = _read("release.yml")
    assert "merge-base --is-ancestor" in text and "origin/main" in text
    assert re.search(r"^permissions:\n  contents: read\n", text, re.M)
    assert "packages: write" in _job_block(text, "publish")
    assert "packages: write" not in _job_block(text, "deploy")


def test_scripts_de_producao_sao_executaveis_no_git():
    """Na VPS vale o modo gravado no git (o checkout --force do deploy reaplica o modo).
    Sem +x, `scripts/prod/x.sh` falha com Permission denied."""
    try:
        out = subprocess.run(["git", "ls-files", "-s", "scripts/prod", "docker"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):  # pragma: no cover
        pytest.skip("git indisponível")
    if not out.strip():  # pragma: no cover - árvore sem metadados do git (ex.: cópia)
        pytest.skip("sem índice git")
    sem_x = [line.split("\t")[1] for line in out.splitlines()
             if line.split("\t")[1].endswith(".sh") and not line.startswith("100755")]
    assert not sem_x, f"scripts sem bit de execução no git: {sem_x}"


def test_credencial_ghcr_vai_por_stdin_e_nao_por_argumento():
    deploy = _job_block(_read("release.yml"), "deploy")
    assert re.search(r"printf '%s\\n%s\\n' \"\$PULL_USER\" \"\$PULL_TOKEN\" \| ssh", deploy)
    cmd = re.search(r'"set -euo pipefail; cd .*?"', deploy, re.S).group(0)
    assert "PULL_TOKEN" not in cmd and "GITHUB_TOKEN" not in cmd


@pytest.mark.skipif(not (ROOT / "scripts/prod/validate-tag.sh").exists(), reason="script ausente")
@pytest.mark.parametrize("tag,ok", [
    ("v1.0.0", True), ("v0.0.1", True), ("v10.20.30", True),
    ("1.0.0", False), ("v1.0", False), ("v1.0.0-rc1", False), ("v1.0.0.1", False),
    ("v01.0.0", False), ("V1.0.0", False), ("v1.0.0'; rm -rf /", False), ("", False), ("latest", False),
])
def test_validate_tag(tag, ok):
    try:
        proc = subprocess.run(["bash", str(ROOT / "scripts/prod/validate-tag.sh"), tag], capture_output=True, text=True)
    except FileNotFoundError:  # pragma: no cover - sem bash (Windows puro)
        pytest.skip("bash indisponível")
    assert (proc.returncode == 0) is ok
    if ok:
        assert proc.stdout.strip() == tag
