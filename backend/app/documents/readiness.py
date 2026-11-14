"""Prontidão de documentos para análise (somente leitura, sem migration).

Problema (auditoria v1.0.2): o status do documento mostrava "CONCLUIDO" mesmo sem texto
extraído, sem OCR e sem embeddings, então um PDF escaneado em branco parecia pronto.

Aqui o estado é DERIVADO do que já está persistido (``extraction_metadata``, chunks e
``DocumentVersion.status``) e exposto em etapas explícitas:

    upload -> ocr -> extração -> chunking -> embedding -> indexação

``pronto_para_analise`` é verdadeiro quando há texto utilizável e chunks (busca por texto
funciona mesmo sem embeddings). ``nivel_indexacao`` diz o que de fato existe:
``vetorial`` (todos os chunks com embedding), ``parcial``, ``texto`` ou ``nenhum``.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from . import states


def blocking_state(extraction: dict[str, Any] | None, chunk_count: int) -> str | None:
    """Estado terminal "não pronto" que impede o uso do documento, ou ``None`` se há texto utilizável."""
    meta = extraction or {}
    if meta.get("ocr_error") or meta.get("ocr_note"):
        return states.OCR_FALHOU
    if meta.get("ocr_pending"):
        return states.OCR_NECESSARIO
    chars = meta.get("char_count")  # ausente = desconhecido (decide só pelos chunks)
    if chunk_count == 0 or (chars is not None and int(chars) == 0):
        return states.SEM_TEXTO
    if meta.get("extraction_quality") == "INSUFICIENTE":
        return states.SEM_TEXTO
    return None


def _counts(db: Session, version_id: int) -> tuple[int, int]:
    total, embedded = db.execute(
        select(func.count(models.DocumentChunk.id), func.count(models.DocumentChunk.embedding)).where(
            models.DocumentChunk.document_version_id == version_id
        )
    ).one()
    return int(total or 0), int(embedded or 0)


def _stage(name: str, state: str, detail: str = "") -> dict[str, str]:
    return {"etapa": name, "estado": state, "detalhe": detail}


def version_processing(db: Session, version: models.DocumentVersion) -> dict[str, Any]:
    """Etapas de processamento e prontidão de UMA versão de documento."""
    meta = dict(version.extraction_metadata or {})
    total, embedded = _counts(db, version.id)
    status = version.status or states.RECEBIDO
    block = status if status in states.NOT_READY_STATES else blocking_state(meta, total)
    chars_meta = meta.get("char_count")
    has_text = block not in (states.SEM_TEXTO, states.OCR_NECESSARIO, states.OCR_FALHOU) and total > 0 and (chars_meta is None or int(chars_meta) > 0)

    # --- OCR
    if meta.get("ocr") and meta.get("ocr_truncated"):
        ocr = _stage("ocr", "parcial", f"OCR leu {meta.get('ocr_pages')} de {meta.get('ocr_pages_total')} páginas (limite configurado). O restante NÃO foi lido.")
    elif meta.get("ocr"):
        ocr = _stage("ocr", "concluida", "Texto obtido por OCR local (Tesseract).")
    elif meta.get("ocr_error") or meta.get("ocr_note"):
        ocr = _stage("ocr", "falhou", "O OCR foi executado, mas falhou ou não melhorou a extração. Reenvie um arquivo mais legível.")
    elif meta.get("ocr_pending"):
        why = "O OCR está desligado" if not settings.ocr_enabled else "O motor de OCR não está disponível neste ambiente"
        ocr = _stage("ocr", "indisponivel", f"Documento digitalizado sem camada de texto. {why}; o conteúdo não foi lido.")
    else:
        ocr = _stage("ocr", "nao_aplicavel", "Documento com texto digital; OCR desnecessário.")

    # --- Extração
    if status == states.ERRO:
        extracao = _stage("extracao", "falhou", "Falha ao processar o arquivo.")
    elif has_text:
        extracao = _stage("extracao", "concluida", f"{int(chars_meta)} caracteres extraídos." if chars_meta is not None else "Texto extraído.")
    else:
        extracao = _stage("extracao", "falhou", "Nenhum texto utilizável foi extraído.")

    # --- Chunking
    chunking = _stage("chunking", "concluida", f"{total} trechos criados.") if total > 0 else _stage("chunking", "falhou" if status in states.NOT_READY_STATES else "pendente", "Nenhum trecho criado.")

    # --- Embedding / indexação
    if block in (states.SEM_TEXTO, states.OCR_NECESSARIO, states.OCR_FALHOU) or status == states.ERRO:
        embedding = _stage("embedding", "nao_aplicavel", "Sem texto utilizável; nada a vetorizar.")
        indexacao = _stage("indexacao", "falhou", "Documento fora do índice de busca.")
        nivel = "nenhum"
    elif total > 0 and embedded == total:
        embedding = _stage("embedding", "concluida", f"{embedded}/{total} trechos com embedding.")
        indexacao = _stage("indexacao", "concluida", "Indexado por busca vetorial e por texto.")
        nivel = "vetorial"
    elif embedded > 0:
        embedding = _stage("embedding", "parcial", f"{embedded}/{total} trechos com embedding.")
        indexacao = _stage("indexacao", "parcial", "Indexado por texto; busca vetorial incompleta.")
        nivel = "parcial"
    elif not settings.effective_llm_api_key:
        embedding = _stage("embedding", "indisponivel", "Sem chave de IA: embeddings pendentes. A busca por texto continua ativa.")
        indexacao = _stage("indexacao", "parcial", "Indexado apenas por texto (sem vetores).")
        nivel = "texto" if total > 0 else "nenhum"
    else:
        last_error = meta.get("embedding_last_error")
        embedding = _stage("embedding", "falhou" if last_error else "pendente", (str(last_error)[:200] if last_error else "Aguardando o worker gerar os embeddings."))
        indexacao = _stage("indexacao", "parcial", "Indexado apenas por texto até os embeddings serem gerados.")
        nivel = "texto" if total > 0 else "nenhum"

    pronto = block is None and total > 0 and has_text
    if status == states.ERRO:
        exibicao, mensagem = "ERRO", "Falha ao processar o documento."
    elif block == states.OCR_NECESSARIO:
        exibicao, mensagem = "OCR_NECESSARIO", "Documento digitalizado: o texto não foi extraído (OCR indisponível). Não está pronto para análise."
    elif block == states.OCR_FALHOU:
        exibicao, mensagem = "OCR_FALHOU", "O OCR falhou ou não melhorou a leitura. Não está pronto para análise."
    elif block == states.SEM_TEXTO:
        exibicao, mensagem = "SEM_TEXTO", "Nenhum texto utilizável foi extraído. Não está pronto para análise."
    elif nivel == "vetorial":
        exibicao, mensagem = "INDEXADO", "Pronto: texto extraído e indexado (busca vetorial e por texto)."
    elif nivel == "parcial":
        exibicao, mensagem = "INDEXADO_PARCIAL", "Pronto por texto; embeddings incompletos."
    elif pronto:
        exibicao, mensagem = "PRONTO_SEM_EMBEDDING", "Pronto por busca de texto; embeddings ainda não gerados."
    elif status in (states.RECEBIDO, states.EXTRAINDO, states.EXTRAIDO, states.PROCESSANDO_EMBEDDING, states.AGUARDANDO_EMBEDDING, states.LEGADO_PROCESSANDO):
        exibicao, mensagem = "PROCESSANDO", "Processamento em andamento."
    else:
        exibicao, mensagem = "SEM_TEXTO", "Sem texto utilizável. Não está pronto para análise."

    return {
        "estado": exibicao,
        "mensagem": mensagem,
        "pronto_para_analise": bool(pronto),
        "nivel_indexacao": nivel,
        "chunks": total,
        "chunks_com_embedding": embedded,
        "etapas": [_stage("upload", "concluida", "Arquivo original preservado."), ocr, extracao, chunking, embedding, indexacao],
    }


def property_documents_summary(db: Session, property_id: int) -> dict[str, Any]:
    """Resumo de prontidão dos documentos do imóvel (versão mais recente de cada um)."""
    documents = db.scalars(select(models.Document).where(models.Document.property_id == property_id).order_by(models.Document.id)).all()
    items: list[dict[str, Any]] = []
    for document in documents:
        # Consulta explícita (não a coleção ``document.versions``, que pode estar desatualizada na sessão).
        latest = db.scalars(
            select(models.DocumentVersion).where(models.DocumentVersion.document_id == document.id).order_by(models.DocumentVersion.version.desc()).limit(1)
        ).first()
        if latest is None:
            continue
        info = version_processing(db, latest)
        items.append({"documento_id": document.id, "nome": document.name, "versao": latest.version, "estado": info["estado"], "pronto": info["pronto_para_analise"], "mensagem": info["mensagem"]})
    ready = [i for i in items if i["pronto"]]
    return {"total": len(items), "prontos": len(ready), "nao_prontos": [i for i in items if not i["pronto"]], "itens": items}
