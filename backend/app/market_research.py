"""Pesquisa automática do imóvel (v1.0.14): venda, aluguel, condomínio e portal do IPTU por API de pesquisa autorizada.

Monta as consultas a partir do cadastro (tipo, quartos, bairro, cidade, UF e nome do condomínio/empreendimento quando
aparece no título ou na descrição), chama ``search.service`` (cache, retry, provedor alternativo), extrai os anúncios do
título/trecho devolvido (``search.extract``), descarta páginas de listagem, duplicatas e textos sem preço, e grava os
anúncios utilizáveis como ``MarketComparable`` com fonte, URL, data da coleta e confiança. Esses comparáveis entram no
mesmo cálculo de mercado, condomínio e Financeiro dos comparáveis manuais (fonte única). Preço é sempre ANUNCIADO.

Sem provedor configurado: devolve NAO_CONFIGURADO, não grava comparável e não inventa dado.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .search import extract, service

KINDS = ("VENDA", "ALUGUEL", "CONDOMINIO", "IPTU_PORTAL")
_BUILDING = re.compile(r"\b((?:Condom[íi]nio|Residencial|Edif[íi]cio|Ed\.|Conjunto|Vila|Parque)\s+[A-ZÀ-Ú0-9][\wÀ-ú'\- ]{2,40}?)(?=[,.;\-]|\s+-|\s+(?:em|no|na|apto|apartamento|bloco|torre)\b|$)",
                       re.IGNORECASE)
SOURCE_PREFIX = "Pesquisa automática"


def building_name(prop: models.Property) -> str | None:
    """Nome do condomínio/empreendimento quando o cadastro o traz (título, descrição, endereço). Nunca deduzido."""
    for text in (prop.title, prop.description, prop.address):
        m = _BUILDING.search(str(text or ""))
        if m:
            return " ".join(m.group(1).split())
    return None


def queries(prop: models.Property, kinds: tuple[str, ...] = KINDS) -> list[tuple[str, str, list[str] | None]]:
    tipo = (prop.property_type or "Apartamento").strip()
    beds = f" {prop.bedrooms} quartos" if prop.bedrooms else ""
    where = " ".join(x for x in (prop.neighborhood, prop.city, prop.state) if x)
    city = " ".join(x for x in (prop.city, prop.state) if x)
    bname = building_name(prop)
    out: list[tuple[str, str, list[str] | None]] = []
    if "VENDA" in kinds:
        if bname:
            out.append(("VENDA", f"{bname} {city} {tipo} à venda", None))
        out.append(("VENDA", f"{tipo}{beds} à venda {where}", None))
    if "ALUGUEL" in kinds:
        if bname:
            out.append(("ALUGUEL", f"{bname} {city} {tipo} para alugar", None))
        out.append(("ALUGUEL", f"{tipo}{beds} para alugar {where}", None))
    if "CONDOMINIO" in kinds:
        out.append(("CONDOMINIO", f"{bname or prop.address} {city} valor do condomínio", None))
    if "IPTU_PORTAL" in kinds and prop.city:
        out.append(("IPTU_PORTAL", f"consulta débitos IPTU prefeitura {city}", ["gov.br"]))
    return out[: max(1, settings.search_max_queries_per_run)]


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _subject_text(prop: models.Property) -> dict[str, str]:
    return {"city": extract.fold(prop.city or ""), "neighborhood": extract.fold(prop.neighborhood or ""), "type": extract.fold(prop.property_type or "")}


def _existing_urls(prop: models.Property) -> set[str]:
    return {extract.normalize_url(c.url) for c in prop.comparables if c.url}


def _to_comparable(prop: models.Property, row: dict[str, Any], provider: str, hit: dict[str, Any], today: date) -> models.MarketComparable:
    subject = _subject_text(prop)
    text = extract.fold(f"{hit.get('title') or ''} {hit.get('snippet') or ''}")
    kind = row["tipo"]
    note = (f"Extraído do resultado de pesquisa ({provider}): título e trecho devolvidos pela API, sem abrir o portal. Preço anunciado, "
            f"não transação. Confiança {row['confianca']}. Confira no anúncio.")
    if row.get("taxa_extra_mencionada"):
        note += " O texto menciona taxa extra/chamada de capital."
    return models.MarketComparable(
        property_id=prop.id, kind=kind,
        price=row["valor"] if kind == "VENDA" else Decimal("0"), rent=row["valor"] if kind == "ALUGUEL" else None,
        area_m2=row["area_m2"] or Decimal("0"), source=f"{SOURCE_PREFIX} ({provider}) — {row['fonte']}"[:240], url=str(row["url"])[:500],
        price_type="ANUNCIADO", collected_at=today, listing_date=_parse_date(row.get("publicado")),
        city=prop.city if subject["city"] and subject["city"] in text else None,
        state=prop.state if subject["city"] and subject["city"] in text else None,
        neighborhood=prop.neighborhood if subject["neighborhood"] and subject["neighborhood"] in text else None,
        property_type=prop.property_type if subject["type"] and subject["type"][:6] in text else None,
        bedrooms=row.get("quartos"), parking_spots=row.get("vagas"), condo_fee=row.get("condominio"), iptu=row.get("iptu"),
        area_basis="DESCONHECIDA" if row.get("area_m2") is not None else None, listing_ref=(row.get("titulo") or "")[:160] or None,
        notes=note, excluded=False,
    )


def run(db: Session, prop: models.Property, *, kinds: tuple[str, ...] = KINDS, now: datetime | None = None,
        chain: list | None = None) -> dict[str, Any]:
    """Executa a pesquisa do imóvel e grava os anúncios utilizáveis como comparáveis. Idempotente pela URL e pelo cache."""
    from .services import record_event
    now = now or datetime.utcnow()
    today = now.date()
    state = service.status()
    if chain is None and not state["ativo"]:
        return {"status": "NAO_CONFIGURADO", "texto": state["texto"], "provedores": state["provedores"], "consultas": [], "comparaveis_criados": [],
                "descartados": [], "referencias_condominio": [], "portais_iptu": [], "taxa_extra_mencionada": []}
    existing = _existing_urls(prop)
    consultas, created, discarded, condo_refs, portals, extras = [], [], [], [], [], []
    listings_all: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    for kind, query, domains in queries(prop, kinds):
        row = service.search(db, kind=kind, query=query, property_id=prop.id, include_domains=domains, chain=chain, now=now)
        consultas.append({"tipo": kind, "consulta": query, "provedor": row.provider, "status": row.status, "resultados": row.results_count,
                          "em": row.created_at or now, "erro": row.error})
        for hit in row.results or []:
            if kind == "IPTU_PORTAL":
                dom = extract.domain(str(hit.get("url") or ""))
                if dom.endswith("gov.br") and "IPTU" in extract.fold(f"{hit.get('title')} {hit.get('snippet')}"):
                    portals.append({"url": hit.get("url"), "titulo": hit.get("title"), "dominio": dom})
                continue
            listing = extract.extract_listing(hit, "ALUGUEL" if kind == "ALUGUEL" else "VENDA")
            if listing["condominio"] is not None:
                condo_refs.append({"valor": listing["condominio"], "url": listing["url"], "fonte": listing["fonte"], "titulo": listing["titulo"],
                                   "coletado_em": today.isoformat()})
            if listing["taxa_extra_mencionada"]:
                extras.append({"url": listing["url"], "titulo": listing["titulo"]})
            if kind in ("VENDA", "ALUGUEL"):
                listings_all.append((listing, hit, row.provider))
    extract.dedupe([x[0] for x in listings_all])
    for listing, hit, provider in listings_all:
        if not listing["utilizavel"] or listing["url_normalizada"] in existing:
            if listing["url_normalizada"] in existing and listing["utilizavel"]:
                listing["motivos"].append("Anúncio já cadastrado neste imóvel.")
            discarded.append({"url": listing["url"], "titulo": listing["titulo"], "motivos": listing["motivos"]})
            continue
        comp = _to_comparable(prop, listing, provider, hit, today)
        db.add(comp); db.flush()
        existing.add(listing["url_normalizada"])
        created.append({"id": comp.id, "tipo": comp.kind, "valor": listing["valor"], "area_m2": listing["area_m2"], "url": comp.url,
                        "fonte": listing["fonte"], "confianca": listing["confianca"]})
    statuses = {c["status"] for c in consultas}
    overall = ("SUCESSO" if "SUCESSO" in statuses else "SEM_RESULTADO" if "SEM_RESULTADO" in statuses else
               "NAO_CONFIGURADO" if statuses == {"NAO_CONFIGURADO"} else "ERRO")
    record_event(db, prop, "PESQUISA_AUTOMATICA_EXECUTADA", "ExternalSearch", None,
                 {"status": overall, "consultas": len(consultas), "comparaveis_criados": [c["id"] for c in created]}, ["mercado", "financeiro", "checklist"])
    if created:
        db.expire(prop, ["comparables"])
    return {"status": overall, "texto": None, "provedores": state["provedores"], "consultas": consultas, "comparaveis_criados": created,
            "descartados": discarded, "referencias_condominio": condo_refs, "portais_iptu": portals, "taxa_extra_mencionada": extras}


def run_if_configured(db: Session, prop: models.Property) -> dict[str, Any] | None:
    """Gancho da análise do imóvel: pesquisa só com provedor configurado e ``SEARCH_AUTO_ON_ANALYSIS``; o cache evita repetir."""
    if not settings.search_auto_on_analysis or not service.status()["ativo"]:
        return None
    return run(db, prop)


def history(db: Session, property_id: int, limit: int = 40) -> dict[str, Any]:
    rows = db.scalars(select(models.ExternalSearch).where(models.ExternalSearch.property_id == property_id)
                      .order_by(models.ExternalSearch.id.desc()).limit(limit)).all()
    latest_portals: list[dict[str, Any]] = []
    for r in rows:
        if r.kind == "IPTU_PORTAL" and r.status == "SUCESSO" and not latest_portals:
            latest_portals = [{"url": h.get("url"), "titulo": h.get("title"), "dominio": extract.domain(str(h.get("url") or ""))}
                              for h in r.results or [] if extract.domain(str(h.get("url") or "")).endswith("gov.br")]
    return {"property_id": property_id, "provedores": service.status(), "portais_iptu": latest_portals,
            "consultas": [{"id": r.id, "tipo": r.kind, "consulta": r.query, "provedor": r.provider, "status": r.status, "resultados": r.results_count,
                           "duracao_ms": r.duration_ms, "tentativas": r.attempts, "custo_estimado_usd": r.cost_estimate_usd, "erro": r.error,
                           "em": r.created_at, "valido_ate": r.expires_at,
                           "itens": [{"url": h.get("url"), "titulo": h.get("title"), "publicado": h.get("published")} for h in (r.results or [])[:10]]}
                          for r in rows]}
