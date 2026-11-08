"""Governança de arquivos de documento (Fase 4) — diagnóstico DRY-RUN.

A auditoria encontrou diretórios ``property-NNNN`` em ``backend_storage`` sem
contrapartida no banco (resíduo de testes). Esta ferramenta INVENTARIA e CLASSIFICA os
diretórios, calculando o espaço recuperável — mas **NÃO exclui nada** nesta missão.

Garantias de segurança:
- ``dry_run=True`` é o padrão e a exclusão real está DESABILITADA (``allow_delete``
  separado). Mesmo habilitada, a exclusão exige confirmação explícita por diretório.
- O imóvel **633** é sempre protegido (``PROTECTED_PROPERTY_IDS``): nunca é candidato.
- Classificação conservadora: na dúvida => ``UNCERTAIN`` (nunca candidato a exclusão).

Classificação por diretório ``property-<id>``:
- ``REFERENCED``   : existe ``properties.id`` = id no banco.
- ``NOT_REFERENCED``: id não existe no banco (candidato — resíduo provável).
- ``UNCERTAIN``    : nome fora do padrão, id não numérico, ou protegido.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models

PROTECTED_PROPERTY_IDS: frozenset[int] = frozenset({633})
_DIR_RE = re.compile(r"^property-(\d+)$")

REFERENCED = "REFERENCED"
NOT_REFERENCED = "NOT_REFERENCED"
UNCERTAIN = "UNCERTAIN"


@dataclass
class DirDiagnosis:
    name: str
    path: str
    property_id: int | None
    classification: str
    size_bytes: int
    file_count: int
    protected: bool
    reason: str


def _dir_size(path: Path) -> tuple[int, int]:
    total = 0
    files = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
                files += 1
            except OSError:
                pass
    return total, files


def diagnose(db: Session, storage_root: str | Path) -> dict:
    """Inventaria e classifica os diretórios de storage (somente leitura).

    Retorna o relatório completo: cada diretório, sua classificação, tamanho e se é
    candidato a limpeza. Não exclui nada.
    """
    root = Path(storage_root)
    base = root / "documents" if (root / "documents").exists() else root
    existing_ids = {pid for (pid,) in db.execute(select(models.Property.id)).all()}

    items: list[DirDiagnosis] = []
    if base.exists():
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            m = _DIR_RE.match(child.name)
            size, files = _dir_size(child)
            if not m:
                items.append(DirDiagnosis(child.name, str(child), None, UNCERTAIN, size, files, False, "nome fora do padrao property-<id>"))
                continue
            pid = int(m.group(1))
            protected = pid in PROTECTED_PROPERTY_IDS
            if protected:
                cls, reason = UNCERTAIN, "imovel protegido (historico) — nunca candidato"
            elif pid in existing_ids:
                cls, reason = REFERENCED, "property existe no banco"
            else:
                cls, reason = NOT_REFERENCED, "property inexistente no banco (residuo provavel)"
            items.append(DirDiagnosis(child.name, str(child), pid, cls, size, files, protected, reason))

    candidates = [i for i in items if i.classification == NOT_REFERENCED and not i.protected]
    return {
        "storage_root": str(base),
        "total_diretorios": len(items),
        "referenciados": sum(1 for i in items if i.classification == REFERENCED),
        "nao_referenciados": len(candidates),
        "incertos": sum(1 for i in items if i.classification == UNCERTAIN),
        "espaco_recuperavel_bytes": sum(i.size_bytes for i in candidates),
        "protegidos": sorted(PROTECTED_PROPERTY_IDS),
        "diretorios": [asdict(i) for i in items],
        "candidatos_limpeza": [i.name for i in candidates],
    }


def cleanup(db: Session, storage_root: str | Path, *, dry_run: bool = True, allow_delete: bool = False, confirm_names: list[str] | None = None) -> dict:
    """Plano de limpeza. Por padrão DRY-RUN e exclusão DESABILITADA.

    A exclusão real só ocorre com ``dry_run=False`` E ``allow_delete=True`` E a lista
    explícita ``confirm_names`` dos diretórios a remover (que precisam ser candidatos
    NOT_REFERENCED e não protegidos). Nesta missão, usar sempre em dry-run.
    """
    report = diagnose(db, storage_root)
    plano = {
        "dry_run": dry_run,
        "allow_delete": allow_delete,
        "candidatos": report["candidatos_limpeza"],
        "espaco_recuperavel_bytes": report["espaco_recuperavel_bytes"],
        "removidos": [],
        "motivo": "",
    }
    if dry_run or not allow_delete:
        plano["motivo"] = "dry-run (padrao): nada removido. Para executar: dry_run=False, allow_delete=True e confirm_names explicitos."
        return plano

    confirm = set(confirm_names or [])
    candidatos = set(report["candidatos_limpeza"])
    alvo = confirm & candidatos  # só remove o que foi confirmado E é candidato seguro
    import shutil

    base = Path(report["storage_root"])
    removed = []
    for name in sorted(alvo):
        # Defesa extra: jamais remover protegido ou fora do padrão.
        m = _DIR_RE.match(name)
        if not m or int(m.group(1)) in PROTECTED_PROPERTY_IDS:
            continue
        target = base / name
        if target.is_dir():
            shutil.rmtree(target)
            removed.append(name)
    plano["removidos"] = removed
    plano["motivo"] = f"removidos {len(removed)} diretorio(s) confirmado(s)"
    return plano
