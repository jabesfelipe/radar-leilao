"""Categorias/domínios de análise de cada documento (metadata dos chunks).

Problema (auditoria de homologação v1.0.2): o RAG filtrava por ``metadata_json->>'category'``,
mas a ingestão NUNCA gravava ``category``; qualquer busca por domínio (``juridico`` etc.)
retornava 0 chunks. Aqui definimos, de forma determinística e sem IA, a quais domínios de
análise cada tipo de documento serve:

- ``domains``: lista de domínios em que o documento é relevante (um documento serve a vários);
- ``category``: domínio principal (primeiro de ``domains``), mantido por compatibilidade.

Tipo desconhecido => todos os domínios (nunca esconder um documento do RAG por não saber o tipo).
"""
from __future__ import annotations

import unicodedata

DOMAINS: tuple[str, ...] = ("documental", "juridico", "financeiro", "mercado", "checklist")

# (fragmento do tipo normalizado, domínios — o primeiro é a categoria principal)
_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("MATRIC",), ("documental", "juridico", "checklist")),
    (("EDITAL",), ("documental", "juridico", "financeiro", "checklist")),
    (("CERTID", "PROCESS", "SENTEN", "PENHORA", "ONUS", "ACORDAO", "MANDADO"), ("juridico", "documental", "checklist")),
    (("IPTU", "CONDOM", "DEBITO", "BOLETO", "FATURA", "COMISS", "ITBI", "TAXA"), ("financeiro", "documental", "checklist")),
    (("LAUDO", "AVALIA", "COMPARAV", "MERCADO", "VISTORIA"), ("mercado", "financeiro", "documental")),
)


def normalize_type(document_type: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(document_type or "")).encode("ascii", "ignore").decode("ascii")
    return text.strip().upper()


def domains_for(document_type: str | None) -> list[str]:
    normalized = normalize_type(document_type)
    for fragments, domains in _RULES:
        if any(fragment in normalized for fragment in fragments):
            return list(domains)
    return list(DOMAINS)


def chunk_category_metadata(document_type: str | None) -> dict[str, object]:
    domains = domains_for(document_type)
    return {"category": domains[0], "domains": domains}
