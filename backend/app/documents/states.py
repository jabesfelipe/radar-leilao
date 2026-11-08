"""Vocabulário canônico dos estados de processamento de documentos/versões (RAG).

Motivação (Fase 2 — RAG production-ready): padronizar os estados de
``Document.status`` / ``DocumentVersion.status`` que hoje são strings livres
(`RECEBIDO`/`PROCESSANDO`/`PROCESSADO`/`ERRO`). Este módulo é **declarativo** (sem
I/O, sem migration): as colunas já são ``String`` e aceitam estes valores. Mantém
compatibilidade com os valores legados já persistidos no banco (ex.: `PROCESSADO`).

O ciclo de vida de uma *versão* é:

    RECEBIDO -> EXTRAINDO -> EXTRAIDO -> AGUARDANDO_EMBEDDING
             -> PROCESSANDO_EMBEDDING -> INDEXADO -> CONCLUIDO
    (qualquer etapa) -> ERRO | CANCELADO
    (conteúdo idêntico reaproveitado) -> REAPROVEITADO

Compatibilidade: ``PROCESSADO`` (legado) é tratado como equivalente terminal de
``CONCLUIDO``. Nada é reescrito no histórico; o mapeamento só orienta leitura/UX.
"""
from __future__ import annotations

# --- Estados canônicos da versão de documento ---------------------------------
RECEBIDO = "RECEBIDO"
EXTRAINDO = "EXTRAINDO"
EXTRAIDO = "EXTRAIDO"
AGUARDANDO_EMBEDDING = "AGUARDANDO_EMBEDDING"
PROCESSANDO_EMBEDDING = "PROCESSANDO_EMBEDDING"
INDEXADO = "INDEXADO"
CONCLUIDO = "CONCLUIDO"
ERRO = "ERRO"
CANCELADO = "CANCELADO"
REAPROVEITADO = "REAPROVEITADO"  # conteúdo idêntico a uma versão já processada

# Estado legado persistido no banco antes da Fase 2 (equivalente a CONCLUIDO).
LEGADO_PROCESSADO = "PROCESSADO"
LEGADO_PROCESSANDO = "PROCESSANDO"

VERSION_STATES: tuple[str, ...] = (
    RECEBIDO, EXTRAINDO, EXTRAIDO, AGUARDANDO_EMBEDDING, PROCESSANDO_EMBEDDING,
    INDEXADO, CONCLUIDO, ERRO, CANCELADO, REAPROVEITADO,
    LEGADO_PROCESSADO, LEGADO_PROCESSANDO,
)

# Estados em que a versão está "pronta" (texto extraído + chunks criados). Inclui o
# legado para não reclassificar o histórico.
TERMINAL_OK_STATES: frozenset[str] = frozenset({CONCLUIDO, INDEXADO, REAPROVEITADO, LEGADO_PROCESSADO})
TERMINAL_STATES: frozenset[str] = TERMINAL_OK_STATES | {ERRO, CANCELADO}


def is_terminal(status: str | None) -> bool:
    return (status or "") in TERMINAL_STATES


def is_ok(status: str | None) -> bool:
    return (status or "") in TERMINAL_OK_STATES


def normalize_legacy(status: str | None) -> str:
    """Normaliza estados legados para o vocabulário canônico (apenas leitura/UX)."""
    if status == LEGADO_PROCESSADO:
        return CONCLUIDO
    if status == LEGADO_PROCESSANDO:
        return PROCESSANDO_EMBEDDING
    return status or RECEBIDO
