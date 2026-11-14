"""Diagnóstico de UMA análise (somente leitura): o que rodou, quanto custou, o que foi lido e por que o
veredito saiu assim. Feito para investigar os testes reais com LLM sem abrir o banco à mão.

Uso (local ou no contêiner do backend):
    python -m app.diagnostics <analysis_id> [--saida DIR]      # grava diagnostico-<id>.json e .md

Privacidade: todo texto passa por ``redact_pii`` (CPF, RG, e-mail, telefone, dados bancários) e pelo
pseudonimizador do imóvel (titular, partes, ocupantes viram papéis). Nenhum segredo é lido: chaves e
configuração do provider não entram no diagnóstico. Trechos de documento são cortados em 300 caracteres.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .privacy import redact_pii

EXCERPT = 300


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean(value: Any, mask) -> Any:
    if isinstance(value, str):
        return mask(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _clean(v, mask) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v, mask) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _masker(db: Session, property_id: int):
    try:
        from .privacy_context import aliaser_for_property
        aliaser = aliaser_for_property(db, property_id)
        return lambda text: aliaser.apply(redact_pii(text, force=True))
    except Exception:  # pseudonimização indisponível: mantém a máscara de identificadores
        return lambda text: redact_pii(text, force=True)


def _run(run: models.LLMRun) -> dict[str, Any]:
    return {
        "id": run.id, "agente": run.agent, "status": run.status, "provider": run.provider, "modelo": run.model,
        "duracao_ms": run.duration_ms, "tokens_entrada": run.input_tokens, "tokens_saida": run.output_tokens,
        "custo_usd": _num(run.total_cost), "erro_tipo": run.error_type, "erro": run.error_message,
        "chunks_recuperados": list(run.retrieved_chunk_ids or []), "request_id": run.request_id,
        "criado_em": getattr(run, "created_at", None),
    }


def build_diagnostic(db: Session, analysis_id: int) -> dict[str, Any]:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None:
        raise LookupError(f"Análise {analysis_id} não encontrada")
    prop = db.get(models.Property, analysis.property_id)
    mask = _masker(db, prop.id)

    runs = list(db.scalars(select(models.LLMRun).where(models.LLMRun.analysis_id == analysis.id).order_by(models.LLMRun.id)).all())
    # Chamadas do imóvel fora de uma análise (embeddings, extração) ajudam a explicar custo e leitura.
    outras = list(db.scalars(select(models.LLMRun).where(models.LLMRun.property_id == prop.id, models.LLMRun.analysis_id.is_(None)).order_by(models.LLMRun.id)).all())

    chunk_ids = sorted({cid for run in runs for cid in (run.retrieved_chunk_ids or [])})
    referencias = []
    for cid in chunk_ids:
        chunk = db.get(models.DocumentChunk, cid)
        if chunk is None:
            referencias.append({"chunk_id": cid, "situacao": "chunk não encontrado"})
            continue
        version = db.get(models.DocumentVersion, chunk.document_version_id)
        document = version.document if version else None
        referencias.append({
            "chunk_id": cid, "documento": document.name if document else None, "tipo": document.document_type if document else None,
            "versao": version.version if version else None, "pagina": chunk.page, "secao": chunk.section,
            "do_mesmo_imovel": bool(document and document.property_id == prop.id),
            "trecho": (chunk.content or "")[:EXCERPT],
        })

    documentos = []
    for document in prop.documents:
        for version in sorted(document.versions, key=lambda v: v.version):
            meta = version.extraction_metadata or {}
            documentos.append({
                "documento": document.name, "tipo": document.document_type, "versao": version.version, "estado": version.status,
                "metodo_extracao": meta.get("method") or meta.get("extraction_method"), "caracteres": meta.get("char_count"),
                "ocr": {k: meta.get(k) for k in ("ocr_used", "ocr_pages_total", "ocr_truncated") if k in meta} or None,
                "chunks": len(version.chunks) if hasattr(version, "chunks") else None,
            })

    verdict = db.scalar(select(models.Verdict).where(models.Verdict.property_id == prop.id, models.Verdict.analysis_version == analysis.version).order_by(models.Verdict.id.desc()))
    decisao = ((verdict.financial or {}).get("decisao") if verdict else None) or {}

    from .services import execution_for_version
    execution = execution_for_version(prop, analysis.version, db=db)
    checklist = []
    for result in (execution.results if execution else []):
        if result.state != "PENDENTE":
            checklist.append({"chave": result.item.canonical_key if result.item else None, "estado": result.state,
                              "confianca": result.confidence, "resposta": result.answer})
    estados = Counter(result.state for result in (execution.results if execution else []))

    evidencias = []
    for eid in analysis.evidence_ids or []:
        ev = db.get(models.Evidence, eid)
        if ev is None:
            continue
        version = ev.document_version
        evidencias.append({"id": ev.id, "categoria": ev.category, "documento": version.document.name if version and version.document else None,
                           "versao": version.version if version else None, "pagina": ev.page, "secao": ev.section, "chunk_id": ev.chunk_id,
                           "fato": ev.fact, "trecho": (ev.source_excerpt or "")[:EXCERPT] or None, "confianca": ev.confidence})

    usage = analysis.token_usage or {}
    custo_analise = sum(_num(run.total_cost) or 0 for run in runs)
    custo_outras = sum(_num(run.total_cost) or 0 for run in outras)
    diag = {
        "analise": {"id": analysis.id, "versao": analysis.version, "imovel_id": prop.id, "imovel": prop.title, "escopo": analysis.scope,
                    "criada_em": getattr(analysis, "created_at", None), "modelo": analysis.model, "prompt": analysis.prompt_version,
                    "status": usage.get("status"), "status_codigo": usage.get("status_codigo"), "status_mensagem": usage.get("status_mensagem"),
                    "avisos": usage.get("avisos", []), "agentes_executados": analysis.agents_executed or []},
        "agentes": [_run(run) for run in runs],
        "chamadas_do_imovel_fora_da_analise": [_run(run) for run in outras],
        "custo": {"analise_usd": round(custo_analise, 6), "embeddings_e_extracao_usd": round(custo_outras, 6),
                  "tokens_entrada": sum(run.input_tokens or 0 for run in runs), "tokens_saida": sum(run.output_tokens or 0 for run in runs),
                  "observacao": "Embeddings têm tokens ESTIMADOS; retries internos do SDK não aparecem. Conferir o painel da OpenAI."},
        "documentos": documentos,
        "rag_referencias": referencias,
        "evidencias": evidencias,
        "checklist": {"por_estado": dict(estados), "resolvidos": checklist},
        "veredito": {
            "overall": verdict.overall if verdict else None, "resumo": verdict.summary if verdict else None,
            "recomendacao": decisao.get("recomendacao"), "avaliacao_financeira": (decisao.get("avaliacao_financeira") or {}).get("status"),
            "motivos_financeiros": (decisao.get("avaliacao_financeira") or {}).get("motivos", []),
            "faltantes_financeiros": (decisao.get("avaliacao_financeira") or {}).get("faltantes", []),
            "fundamentos": decisao.get("fundamentos", []), "pendencias": (verdict.pending_items if verdict else []) or [],
        },
    }
    return _clean(diag, mask)


def to_markdown(d: dict[str, Any]) -> str:
    a, v, c = d["analise"], d["veredito"], d["custo"]
    rec = v.get("recomendacao") or {}
    linhas = [
        f"# Diagnóstico da análise {a['id']} (v{a['versao']}) — imóvel {a['imovel_id']}", "",
        f"- Status: `{a.get('status')}` / `{a.get('status_codigo')}` — {a.get('status_mensagem') or ''}",
        f"- Modelo: {a.get('modelo') or '—'} · agentes: {', '.join(a.get('agentes_executados') or []) or '—'}",
        f"- Veredito: **{v.get('overall')}** · recomendação: **{rec.get('codigo', '—')}** — {rec.get('texto', '—')}",
        f"- Avaliação financeira: {v.get('avaliacao_financeira') or '—'}",
        f"- Custo: análise US$ {c['analise_usd']:.4f} · embeddings/extração US$ {c['embeddings_e_extracao_usd']:.4f} · tokens {c['tokens_entrada']}/{c['tokens_saida']}", "",
        "## Agentes", "", "| Agente | Status | Modelo | ms | Tokens in/out | US$ | Chunks | Erro |", "|---|---|---|---|---|---|---|---|",
    ]
    for r in d["agentes"] + d["chamadas_do_imovel_fora_da_analise"]:
        linhas.append(f"| {r['agente']} | {r['status']} | {r['modelo']} | {r['duracao_ms'] or '—'} | {r['tokens_entrada'] or '—'}/{r['tokens_saida'] or '—'} | {r['custo_usd'] if r['custo_usd'] is not None else '—'} | {len(r['chunks_recuperados'])} | {(r['erro'] or '')[:80]} |")
    linhas += ["", "## Documentos", ""] + [f"- {x['documento']} v{x['versao']} ({x['tipo']}): {x['estado']} · chunks {x['chunks']} · extração {x['metodo_extracao'] or '—'}" for x in d["documentos"]]
    linhas += ["", "## Trechos recuperados (RAG)", ""] + [f"- chunk {x['chunk_id']} · {x.get('documento')} v{x.get('versao')} · pág. {x.get('pagina') or '—'} · seção {x.get('secao') or '—'}{'' if x.get('do_mesmo_imovel', True) else ' · **OUTRO IMÓVEL**'}" for x in d["rag_referencias"]]
    linhas += ["", "## Evidências", ""] + [f"- #{x['id']} {x['categoria']} · {x['documento'] or 'sem documento'} · pág. {x['pagina'] or '—'} · seção {x['secao'] or '—'}: {x['fato']}" for x in d["evidencias"]]
    linhas += ["", "## Fundamentos do veredito", ""] + [f"- [{f.get('tipo')}] {f.get('descricao')}" for f in v.get("fundamentos") or []]
    linhas += ["", f"Checklist por estado: {json.dumps(d['checklist']['por_estado'], ensure_ascii=False)}", "",
               "> Texto mascarado (identificadores pessoais e nomes conhecidos do imóvel). Sem segredos."]
    return "\n".join(linhas) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta o diagnóstico de uma análise (JSON + Markdown).")
    parser.add_argument("analysis_id", type=int)
    parser.add_argument("--saida", default=".", help="diretório de saída")
    args = parser.parse_args()
    from .database import SessionLocal
    db = SessionLocal()
    try:
        diag = build_diagnostic(db, args.analysis_id)
    finally:
        db.close()
    out = Path(args.saida)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"diagnostico-{args.analysis_id}.json").write_text(json.dumps(diag, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / f"diagnostico-{args.analysis_id}.md").write_text(to_markdown(diag), encoding="utf-8")
    print(f"diagnostico gravado em {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
