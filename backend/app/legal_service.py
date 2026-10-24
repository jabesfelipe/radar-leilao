"""Serviços da Central Jurídica (determinísticos; sem LLM nos caminhos de leitura).

Camada de aplicação que:
  1. materializa o catálogo curado (``legal_catalog``) de forma idempotente (seed);
  2. serve a BIBLIOTECA jurídica (listagem + busca), reaproveitando o embedding do
     projeto quando há API key e caindo para busca textual determinística quando não
     há (mesmo padrão de ``knowledge_memory``/``RAGService``);
  3. entrega REFERÊNCIAS CONTEXTUAIS: dado um ``canonical_key`` do checklist ou uma
     etapa/contexto, devolve as regras + dispositivos aplicáveis (é isso que faz a
     base legal "aparecer em contexto", não como uma lista solta);
  4. consolida uma visão jurídica do imóvel reutilizando ``juridical_overview``.

NUNCA fabrica norma. Distingue texto oficial (``official_text``) de orientação
(``practical_note``) e expõe ``verification_status`` para o usuário saber o que já
foi conferido.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .checklist import CHECKLIST_MASTER
from .legal_catalog import RULES, SOURCES, RuleSeed, SourceSeed


# Mapa canonical_key -> (question, category) para anotar os vínculos de checklist.
_CHECKLIST_INDEX: dict[str, tuple[str, str]] = {
    key: (question, category) for (key, question, category, _origin) in CHECKLIST_MASTER
}


# ---------------------------------------------------------------------------
# SEED (idempotente)
# ---------------------------------------------------------------------------

def _embed_or_none(text: str) -> list[float] | None:
    """Gera embedding do verbete da biblioteca quando o provedor está configurado.

    Sem API key (ex.: ambiente de teste), retorna None — a biblioteca continua
    funcional via busca textual. Qualquer falha é silenciada: indexação semântica é
    um reforço, nunca um requisito para servir a base legal."""
    try:
        from .config import settings
        if not settings.effective_llm_api_key:
            return None
        from .rag.embeddings import generate_embedding
        return generate_embedding(text)
    except Exception:
        return None


def _library_item_for(db: Session, slug: str) -> models.KnowledgeItem | None:
    return db.scalar(
        select(models.KnowledgeItem).where(
            models.KnowledgeItem.kind == models.LEGAL_LIBRARY_KIND,
            models.KnowledgeItem.metadata_json["provision_slug"].as_string() == slug,
        )
    )


def seed_legal_catalog(db: Session, *, embed: bool = True) -> dict[str, int]:
    """Materializa o catálogo curado (upsert por slug). Idempotente: rodar N vezes
    não duplica nada e não sobrescreve ``verification_status`` humano já promovido a
    VERIFICADO para algo inferior.

    Retorna contadores do que foi criado (para logs/diagnóstico)."""
    created = {"sources": 0, "provisions": 0, "rules": 0, "links": 0, "library": 0}

    source_by_slug: dict[str, models.LegalSource] = {}
    provision_by_slug: dict[str, models.LegalProvision] = {}

    for src in SOURCES:
        row = db.scalar(select(models.LegalSource).where(models.LegalSource.slug == src.slug))
        if row is None:
            row = models.LegalSource(
                slug=src.slug, source_type=src.source_type, label=src.label, title=src.title,
                authority=src.authority, official_url=src.official_url, year=src.year,
                in_force=src.in_force, verification_status=src.verification_status, summary=src.summary,
            )
            db.add(row); db.flush(); created["sources"] += 1
        source_by_slug[src.slug] = row

        for prov in src.provisions:
            prow = db.scalar(select(models.LegalProvision).where(models.LegalProvision.slug == prov.slug))
            if prow is None:
                prow = models.LegalProvision(
                    source_id=row.id, slug=prov.slug, reference=prov.reference, heading=prov.heading,
                    official_text=prov.official_text, practical_note=prov.practical_note,
                    contexts=list(prov.contexts), tags=list(prov.tags),
                    verification_status=prov.verification_status,
                )
                db.add(prow); db.flush(); created["provisions"] += 1
            provision_by_slug[prov.slug] = prow

            # Biblioteca RAG: 1 KnowledgeItem por dispositivo (kind=LEGAL_LIBRARY).
            lib = _library_item_for(db, prov.slug)
            if lib is None:
                content_parts = [f"{src.label} — {prov.reference}"]
                if prov.heading:
                    content_parts.append(prov.heading)
                if prov.official_text:
                    content_parts.append(prov.official_text)
                if prov.practical_note:
                    content_parts.append(f"Orientação prática: {prov.practical_note}")
                content = "\n".join(content_parts)
                lib = models.KnowledgeItem(
                    kind=models.LEGAL_LIBRARY_KIND,
                    title=f"{src.label} — {prov.reference}"[:240],
                    content=content,
                    metadata_json={
                        "provision_slug": prov.slug,
                        "source_slug": src.slug,
                        "source_type": src.source_type,
                        "contexts": list(prov.contexts),
                        "tags": list(prov.tags),
                        "verification_status": prov.verification_status,
                    },
                    embedding=_embed_or_none(content) if embed else None,
                )
                db.add(lib); db.flush(); created["library"] += 1
                prow.knowledge_item_id = lib.id
                db.flush()

    for rule in RULES:
        rrow = db.scalar(select(models.LegalRule).where(models.LegalRule.slug == rule.slug))
        if rrow is None:
            provision = provision_by_slug.get(rule.provision_slug) if rule.provision_slug else None
            rrow = models.LegalRule(
                slug=rule.slug, rule_kind=rule.rule_kind, title=rule.title, statement=rule.statement,
                contexts=list(rule.contexts), severity=rule.severity,
                provision_id=provision.id if provision is not None else None, active=True,
            )
            db.add(rrow); db.flush(); created["rules"] += 1

        existing_links = {l.canonical_key for l in rrow.checklist_links}
        for link in rule.links:
            if link.canonical_key in existing_links:
                continue
            # Só vincula a chaves canônicas que EXISTEM no Checklist Mestre (27).
            if link.canonical_key not in _CHECKLIST_INDEX:
                continue
            db.add(models.LegalRuleChecklistLink(
                rule_id=rrow.id, canonical_key=link.canonical_key,
                relevance=link.relevance, note=link.note,
            ))
            created["links"] += 1
    db.flush()
    return created


# ---------------------------------------------------------------------------
# SERIALIZAÇÃO LEGÍVEL
# ---------------------------------------------------------------------------

def _provision_dict(prov: models.LegalProvision, *, with_source: bool = True) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": prov.id,
        "slug": prov.slug,
        "referencia": prov.reference,
        "titulo": prov.heading,
        "texto_oficial": prov.official_text,
        "orientacao_pratica": prov.practical_note,
        "contextos": list(prov.contexts or []),
        "tags": list(prov.tags or []),
        "verificacao": prov.verification_status,
    }
    if with_source and prov.source is not None:
        data["fonte"] = {
            "slug": prov.source.slug, "rotulo": prov.source.label, "tipo": prov.source.source_type,
            "url_oficial": prov.source.official_url, "vigente": prov.source.in_force,
        }
    return data


def _rule_dict(rule: models.LegalRule, *, with_checklist: bool = True) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": rule.id,
        "slug": rule.slug,
        "tipo": rule.rule_kind,
        "titulo": rule.title,
        "enunciado": rule.statement,
        "contextos": list(rule.contexts or []),
        "severidade": rule.severity,
        "base_legal": _provision_dict(rule.provision) if rule.provision is not None else None,
    }
    if with_checklist:
        data["itens_checklist"] = [
            {
                "canonical_key": l.canonical_key,
                "relevancia": l.relevance,
                "nota": l.note,
                "pergunta": _CHECKLIST_INDEX.get(l.canonical_key, (None, None))[0],
                "categoria": _CHECKLIST_INDEX.get(l.canonical_key, (None, None))[1],
            }
            for l in rule.checklist_links
        ]
    return data


# ---------------------------------------------------------------------------
# BIBLIOTECA (listagem + busca)
# ---------------------------------------------------------------------------

def list_sources(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(select(models.LegalSource).order_by(models.LegalSource.year.asc(), models.LegalSource.id.asc())).all()
    out: list[dict[str, Any]] = []
    for s in rows:
        out.append({
            "id": s.id, "slug": s.slug, "tipo": s.source_type, "rotulo": s.label, "titulo": s.title,
            "orgao": s.authority, "url_oficial": s.official_url, "ano": s.year, "vigente": s.in_force,
            "verificacao": s.verification_status, "resumo": s.summary,
            "dispositivos": [_provision_dict(p, with_source=False) for p in sorted(s.provisions, key=lambda x: x.id)],
        })
    return out


def search_library(db: Session, query: str, *, limit: int = 20, context: str | None = None) -> dict[str, Any]:
    """Busca na biblioteca jurídica. Usa similaridade vetorial quando há embeddings
    e API key; caso contrário, busca textual determinística (full-text em PT).

    ``context`` (opcional) filtra por contexto/etapa (LEGAL_CONTEXTS)."""
    normalized = str(query or "").strip()
    limit = max(1, min(int(limit or 20), 100))
    vector_used = False
    results: list[tuple[models.LegalProvision, float | None]] = []

    # 1) Tenta busca vetorial reaproveitando os embeddings do KnowledgeItem.
    embedding = None
    if normalized:
        try:
            from .config import settings
            if settings.effective_llm_api_key:
                from .rag.embeddings import generate_embedding
                embedding = generate_embedding(normalized)
        except Exception:
            embedding = None

    if embedding is not None:
        distance = models.KnowledgeItem.embedding.cosine_distance(embedding).label("distance")
        stmt = (
            select(models.KnowledgeItem, distance)
            .where(models.KnowledgeItem.kind == models.LEGAL_LIBRARY_KIND, models.KnowledgeItem.embedding.is_not(None))
            .order_by(distance.asc(), models.KnowledgeItem.id.asc())
            .limit(limit * 2)
        )
        for item, dist in db.execute(stmt).all():
            prov = db.scalar(select(models.LegalProvision).where(models.LegalProvision.knowledge_item_id == item.id))
            if prov is not None:
                results.append((prov, float(dist)))
        vector_used = True

    # 2) Fallback textual (ou busca principal sem embedding).
    if not results:
        stmt = select(models.LegalProvision).join(models.LegalSource)
        if normalized:
            like = f"%{normalized.lower()}%"
            stmt = stmt.where(
                func.lower(
                    func.coalesce(models.LegalProvision.heading, "") + " "
                    + func.coalesce(models.LegalProvision.official_text, "") + " "
                    + func.coalesce(models.LegalProvision.practical_note, "") + " "
                    + models.LegalProvision.reference + " "
                    + models.LegalSource.label
                ).like(like)
            )
        stmt = stmt.order_by(models.LegalProvision.id.asc()).limit(limit)
        results = [(prov, None) for prov in db.scalars(stmt).all()]

    items: list[dict[str, Any]] = []
    for prov, dist in results:
        if context and context.upper() not in {c.upper() for c in (prov.contexts or [])}:
            continue
        payload = _provision_dict(prov)
        if dist is not None:
            payload["similaridade"] = round(1.0 - dist, 4)
        items.append(payload)
        if len(items) >= limit:
            break

    return {
        "query": normalized,
        "contexto": context,
        "modo_busca": "VETORIAL" if vector_used and items else "TEXTUAL",
        "total": len(items),
        "resultados": items,
    }


# ---------------------------------------------------------------------------
# REFERÊNCIAS CONTEXTUAIS (o coração da Central Jurídica)
# ---------------------------------------------------------------------------

def references_for_checklist_key(db: Session, canonical_key: str) -> dict[str, Any]:
    """Regras + base legal aplicáveis a UM item do checklist (por canonical_key).

    É o que permite a UI mostrar "Base legal e orientações" ao lado do item, sem
    alterar a definição canônica do checklist."""
    key = str(canonical_key or "").strip()
    links = db.scalars(
        select(models.LegalRuleChecklistLink).where(models.LegalRuleChecklistLink.canonical_key == key)
    ).all()
    rules = []
    seen: set[int] = set()
    for link in links:
        rule = link.rule
        if rule is None or not rule.active or rule.id in seen:
            continue
        seen.add(rule.id)
        payload = _rule_dict(rule, with_checklist=False)
        payload["relevancia"] = link.relevance
        payload["nota"] = link.note
        rules.append(payload)
    question, category = _CHECKLIST_INDEX.get(key, (None, None))
    return {
        "canonical_key": key,
        "pergunta": question,
        "categoria": category,
        "existe_no_checklist": key in _CHECKLIST_INDEX,
        "total": len(rules),
        "referencias": rules,
    }


def references_for_context(db: Session, context: str) -> dict[str, Any]:
    """Regras aplicáveis a uma etapa/contexto transversal (ex.: DESOCUPACAO, LEILAO)."""
    ctx = str(context or "").strip().upper()
    rules = db.scalars(select(models.LegalRule).where(models.LegalRule.active.is_(True)).order_by(models.LegalRule.id.asc())).all()
    out = [_rule_dict(r) for r in rules if ctx in {c.upper() for c in (r.contexts or [])}]
    return {"contexto": ctx, "total": len(out), "referencias": out}


def checklist_reference_map(db: Session) -> dict[str, int]:
    """Mapa canonical_key -> nº de referências legais vinculadas (para marcar na UI
    quais itens do checklist têm base legal associada)."""
    rows = db.execute(
        select(models.LegalRuleChecklistLink.canonical_key, func.count(models.LegalRuleChecklistLink.id))
        .group_by(models.LegalRuleChecklistLink.canonical_key)
    ).all()
    return {key: int(count) for key, count in rows}


def library_overview(db: Session) -> dict[str, Any]:
    """Visão agregada da biblioteca (para o hub /api/juridico/biblioteca)."""
    sources = list_sources(db)
    rules = db.scalars(select(models.LegalRule).where(models.LegalRule.active.is_(True)).order_by(models.LegalRule.id.asc())).all()
    cobertura = checklist_reference_map(db)
    total_provisions = sum(len(s["dispositivos"]) for s in sources)
    return {
        "total_fontes": len(sources),
        "total_dispositivos": total_provisions,
        "total_regras": len(rules),
        "itens_checklist_cobertos": len(cobertura),
        "itens_checklist_total": len(_CHECKLIST_INDEX),
        "cobertura_checklist": cobertura,
        "fontes": sources,
        "regras": [_rule_dict(r) for r in rules],
    }


def property_legal_overview(db: Session, prop: models.Property) -> dict[str, Any]:
    """Visão jurídica do imóvel ENRIQUECIDA com a base legal contextual.

    Reaproveita ``juridical_overview`` (processos/pendências/correlação, sem LLM) e
    acrescenta, para cada item jurídico pendente do checklist, as referências legais
    aplicáveis — unindo a situação concreta do imóvel à base de conhecimento."""
    from .services import juridical_overview, latest_execution

    base = juridical_overview(db, prop)
    execution = latest_execution(prop)
    itens: list[dict[str, Any]] = []
    if execution:
        for res in execution.results:
            item = res.item
            if item is None:
                continue
            refs = references_for_checklist_key(db, item.canonical_key)
            if refs["total"] == 0:
                continue
            itens.append({
                "canonical_key": item.canonical_key,
                "pergunta": item.question,
                "estado": res.state,
                "categoria": item.category,
                "referencias": refs["referencias"],
            })
    return {
        "property_id": prop.id,
        "sintese_juridica": base,
        "itens_com_base_legal": itens,
        "total_itens_com_base_legal": len(itens),
    }
