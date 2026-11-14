"""Confronto documental determinístico entre matrícula e edital do MESMO imóvel (v1.0.4).

Sem IA e sem custo: localiza no texto já extraído de cada documento informações que precisam coincidir (área
privativa, número da matrícula) e apresenta as duas fontes lado a lado, com trecho literal e chunk de origem.
Divergência não é irregularidade: é um fato a validar (ex.: área "conforme cadastro do condomínio" × área registral).
Só lê documentos do imóvel informado (isolamento por property_id).
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from . import models

CONFERE = "CONFERE"
DIVERGENCIA = "DIVERGENCIA"
NAO_COMPARAVEL = "NAO_COMPARAVEL"

_AREA_RE = re.compile(r"[áa]rea\s+privativa\s+(?:de\s+|:\s*)?(\d{1,5}(?:\.\d{3})*(?:,\d{1,2})?)\s*m", re.I)
_MATRICULA_RE = re.compile(r"matr[íi]cula\s*(?:n[º°o.]*|n[úu]mero)?\s*:?\s*(\d[\d.\-/]{1,20}\d)", re.I)


def _area(text: str) -> tuple[Decimal | None, str | None]:
    match = _AREA_RE.search(text)
    if not match:
        return None, None
    try:
        return Decimal(match.group(1).replace(".", "").replace(",", ".")), match.group(1)
    except InvalidOperation:
        return None, None


def _matricula(text: str) -> tuple[str | None, str | None]:
    match = _MATRICULA_RE.search(text)
    if not match:
        return None, None
    return re.sub(r"\D", "", match.group(1)), match.group(1)


def _sentence(text: str, raw: str) -> str:
    """Linha/frase literal do documento que contém o valor encontrado."""
    for piece in re.split(r"\n+|(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9])", text):
        if raw in piece:
            return " ".join(piece.split())[:300]
    return raw


def _latest_version(document: models.Document) -> models.DocumentVersion | None:
    versions = sorted(document.versions or [], key=lambda v: v.version)
    return versions[-1] if versions else None


def _find(prop: models.Property, document_type: str, finder: Callable[[str], tuple[Any, str | None]]) -> dict[str, Any] | None:
    for document in sorted(prop.documents or [], key=lambda d: d.id):
        if str(document.document_type or "").upper() != document_type:
            continue
        version = _latest_version(document)
        if version is None:
            continue
        for chunk in sorted(version.chunks or [], key=lambda c: c.chunk_index):
            value, raw = finder(chunk.content or "")
            if value is not None:
                return {"valor": value, "valor_texto": raw, "documento": document.name, "document_version_id": version.id,
                        "chunk_id": chunk.id, "pagina": chunk.page, "trecho": _sentence(chunk.content or "", raw)}
    return None


def _row(informacao: str, matricula: dict | None, edital: dict | None, relevancia: str) -> dict[str, Any]:
    if matricula is None or edital is None:
        falta = "matrícula" if matricula is None else "edital"
        resultado, observacao = NAO_COMPARAVEL, f"Informação não localizada no texto do(a) {falta}; confronto não realizado."
    elif matricula["valor"] == edital["valor"]:
        resultado, observacao = CONFERE, "Os dois documentos informam o mesmo valor."
    else:
        resultado, observacao = DIVERGENCIA, relevancia
    clean = lambda side: None if side is None else {k: (str(v) if isinstance(v, Decimal) else v) for k, v in side.items()}
    return {"informacao": informacao, "matricula": clean(matricula), "edital": clean(edital), "resultado": resultado, "observacao": observacao}


def compare_documents(prop: models.Property) -> list[dict[str, Any]]:
    """Confronto matrícula × edital do imóvel. Lista vazia quando o imóvel não tem os dois documentos."""
    types = {str(d.document_type or "").upper() for d in (prop.documents or [])}
    if not {"MATRICULA", "EDITAL"} <= types:
        return []
    return [
        _row("Área privativa (m²)", _find(prop, "MATRICULA", _area), _find(prop, "EDITAL", _area),
             "Áreas diferentes entre matrícula e edital: confirmar a área registral (prevalece a matrícula) e o impacto no valor "
             "de venda e no preço por m². Não é, por si só, irregularidade."),
        _row("Número da matrícula", _find(prop, "MATRICULA", _matricula), _find(prop, "EDITAL", _matricula),
             "O edital cita matrícula diferente da apresentada: confirmar se o documento corresponde ao imóvel do leilão."),
    ]
