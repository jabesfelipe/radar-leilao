"""Deduplicação de conteúdo documental por hash SHA-256 (Fase 2 — RAG).

Problema observado na auditoria: o mesmo arquivo (ex.: ``EL00440226CPARE.pdf``) foi
ingerido 3 vezes, gerando 3 × 544 chunks idênticos. Reprocessar conteúdo
byte-idêntico não agrega informação — só desperdiça chunks, embeddings e storage.

Estratégia (conservadora e NÃO destrutiva):
- ``content_hash`` = SHA-256 do arquivo original (já calculado no pipeline).
- Dedup é por **documento**: se o novo upload é byte-idêntico à **última versão
  processada** do mesmo documento, reaproveitamos essa versão (não criamos chunks
  nem embeddings novos). Isso evita acúmulo de versões redundantes do mesmo arquivo.
- Identidade de ARQUIVO ≠ identidade de DOCUMENTO de negócio: dois documentos
  distintos (origens/contextos diferentes) podem ter o mesmo conteúdo e continuam
  sendo documentos separados. Por isso o escopo padrão do reaproveitamento é o
  próprio documento, não global — preservando as relações imóvel/oportunidade/origem.
- NÃO há constraint UNIQUE sobre dados existentes (há duplicatas históricas); a
  dedup é aplicada apenas em NOVOS uploads, de forma defensiva.

Este módulo é puro (sem I/O de rede/arquivo); recebe o ``Document`` já carregado.
"""
from __future__ import annotations

import hashlib

from . import states


def content_digest(content: bytes) -> str:
    """SHA-256 hex do conteúdo binário do arquivo original."""
    return hashlib.sha256(content).hexdigest()


def find_reusable_version(document, digest: str):
    """Retorna a versão existente do ``document`` cujo ``content_hash`` seja igual a
    ``digest`` E que já esteja em estado OK (processada/indexada). None se não houver.

    Preferimos a de maior ``version`` (mais recente). Só reaproveitamos versões que
    já concluíram (têm chunks), nunca uma versão em ERRO/parcial.
    """
    candidates = [
        v for v in getattr(document, "versions", [])
        if getattr(v, "content_hash", None) == digest and states.is_ok(getattr(v, "status", None))
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda v: getattr(v, "version", 0) or 0)


def next_version_number(document) -> int:
    """Próximo número de versão do documento (append-only; nunca reusa número)."""
    return max((getattr(v, "version", 0) or 0 for v in getattr(document, "versions", [])), default=0) + 1
