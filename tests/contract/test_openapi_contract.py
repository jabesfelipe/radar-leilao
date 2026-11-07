"""Teste de contrato de API (M0 — modularização).

Garante que a modularização de ``main.py`` em routers NÃO altera o contrato HTTP:
o conjunto de (método, path) exposto pelo ``app`` deve permanecer IDÊNTICO ao
baseline capturado antes do M0 (``openapi_baseline.json``, 99 paths).

Não exige banco: ``app.openapi()`` é estático. Se uma rota for adicionada/removida/
renomeada sem atualizar o baseline conscientemente, este teste falha.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.app.main import app

BASELINE = Path(__file__).with_name("openapi_baseline.json")


def _operations(spec: dict) -> set[str]:
    ops: set[str] = set()
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            ops.add(f"{method.upper()} {path}")
    return ops


def test_openapi_paths_identicos_ao_baseline():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    atual = app.openapi()
    base_ops = _operations(baseline)
    cur_ops = _operations(atual)

    removidas = base_ops - cur_ops
    adicionadas = cur_ops - base_ops

    assert not removidas, f"Rotas removidas/alteradas vs baseline: {sorted(removidas)}"
    assert not adicionadas, f"Rotas novas não registradas no baseline: {sorted(adicionadas)}"


def test_contagem_de_paths_preservada():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    atual = app.openapi()
    assert len(atual.get("paths", {})) == len(baseline.get("paths", {}))
