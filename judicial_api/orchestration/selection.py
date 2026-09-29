"""Seleção de fontes aplicáveis e idempotência (JUR-03).

Regra de seleção (SPEC §3, §12):
- se ``tribunals`` for informado, restringe a essas fontes (resolvendo alias);
- senão, se ``justice_types`` for informado, seleciona as fontes desses ramos;
- senão (pesquisa ampla), seleciona todas as fontes habilitadas;
- em qualquer caso, se ``uf`` for informado, filtra por UF quando a fonte tiver UF
  (fontes nacionais sem UF, ex.: TRFs/superiores, permanecem elegíveis).

Idempotência (SPEC §70): ``compute_request_hash`` gera um hash estável dos
critérios relevantes da consulta, permitindo identificar pesquisas equivalentes.
"""
from __future__ import annotations

import hashlib
import json

from ..catalog.loader import CatalogEntry, JudicialCatalog
from ..models import SearchRequest


def select_sources(request: SearchRequest, catalog: JudicialCatalog) -> list[CatalogEntry]:
    """Retorna as fontes aplicáveis à requisição, respeitando o escopo do catálogo."""
    if request.tribunals:
        selected: list[CatalogEntry] = []
        seen: set[str] = set()
        for token in request.tribunals:
            canonical = catalog.resolve_alias(token)
            if not canonical:
                continue  # fonte fora do escopo/catálogo é ignorada silenciosamente
            entry = catalog.get(canonical)
            if entry and entry.enabled and entry.code not in seen:
                selected.append(entry)
                seen.add(entry.code)
        candidates = selected
    elif request.justice_types:
        candidates = [e for e in catalog.for_justice_types(request.justice_types) if e.enabled]
    else:
        candidates = [e for e in catalog.entries() if e.enabled]

    if request.uf:
        uf = request.uf.strip().upper()
        # Fontes com UF definida devem casar; fontes sem UF (nacionais) permanecem.
        candidates = [e for e in candidates if e.uf is None or e.uf.upper() == uf]

    return candidates


def compute_request_hash(request: SearchRequest) -> str:
    """Hash determinístico dos critérios relevantes (idempotência — SPEC §70)."""
    payload = {
        "name": (request.name or "").strip().lower() or None,
        "cpf": (request.cpf or "").strip() or None,
        "cnpj": (request.cnpj or "").strip() or None,
        "process_number": "".join(ch for ch in (request.process_number or "") if ch.isdigit()) or None,
        "class_code": request.class_code,
        "subject_code": request.subject_code,
        "court_code": request.court_code,
        "grau": (request.grau or "").strip().upper() or None,
        "uf": (request.uf or "").strip().upper() or None,
        "city": (request.city or "").strip().lower() or None,
        "tribunals": sorted({t.strip().upper() for t in request.tribunals}),
        "justice_types": sorted({jt.value for jt in request.justice_types}),
        "include_movements": request.include_movements,
        "include_parties": request.include_parties,
        "include_subjects": request.include_subjects,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
