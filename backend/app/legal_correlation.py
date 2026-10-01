"""Correlação determinística imóvel × processo judicial.

Esta camada é PURA (sem LLM, sem I/O): recebe o perfil conhecido do imóvel e os
dados de um processo (partes, documentos, comarca/tribunal) e classifica o nível
de correlação em ALTA / MEDIA / BAIXA / NAO_CONFIRMADA.

Regra fundamental (SPEC §35-36, §39 e itens 8-9/11 da task):

    EVIDÊNCIA ENCONTRADA  ≠  CORRELAÇÃO COM O IMÓVEL  ≠  FATO CONFIRMADO

- Nome igual NUNCA confirma identidade (homônimo). Só CPF/CNPJ exato confirma.
- "Movimento contendo penhora" NÃO vira "imóvel penhorado": isto aqui classifica
  apenas a probabilidade de o processo se referir ao proprietário/imóvel, não o
  mérito jurídico.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any

# Vocabulário de níveis de correlação (reutilizado na persistência/UI/veredito).
CORRELATION_HIGH = "ALTA"
CORRELATION_MEDIUM = "MEDIA"
CORRELATION_LOW = "BAIXA"
CORRELATION_UNCONFIRMED = "NAO_CONFIRMADA"

# Origem/classificação do vínculo processo×imóvel.
LINK_AUTOMATIC = "AUTOMATICA"
LINK_MANUAL = "MANUAL"
LINK_VALIDATED = "VALIDADA"
LINK_NOT_CONFIRMED = "NAO_CONFIRMADA"


def only_digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def normalize_name(value: Any) -> str:
    """Normaliza nome para comparação: sem acento, minúsculo, espaços colapsados."""
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


def names_match(a: Any, b: Any) -> bool:
    """Correspondência de nome (NÃO confirma identidade). Igualdade exata, ou um
    conjunto de tokens contém o outro quando ambos têm 2+ tokens (nome parcial vs
    completo). Com um único token exige igualdade exata para evitar coincidência."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = set(na.split()), set(nb.split())
    if len(ta) < 2 or len(tb) < 2:
        return False
    return ta.issubset(tb) or tb.issubset(ta)


def _same_comarca(a: Any, b: Any) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    return bool(na) and bool(nb) and (na == nb or na in nb or nb in na)


@dataclass(frozen=True)
class PropertyProfile:
    """Dados conhecidos do imóvel/proprietário relevantes para a correlação.

    Todos opcionais: ausência significa dado desconhecido (nunca presumido)."""
    owner_name: str | None = None
    owner_cpf: str | None = None
    owner_cnpj: str | None = None
    city: str | None = None
    state: str | None = None
    comarca: str | None = None


@dataclass(frozen=True)
class ProcessParty:
    name: str | None = None
    cpf: str | None = None
    cnpj: str | None = None
    role: str | None = None


@dataclass(frozen=True)
class ProcessProfile:
    parties: list[ProcessParty] = field(default_factory=list)
    comarca: str | None = None
    tribunal: str | None = None
    uf: str | None = None


@dataclass(frozen=True)
class CorrelationResult:
    level: str
    reason: str
    matched_party: str | None = None
    criteria: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"nivel": self.level, "motivo": self.reason, "parte": self.matched_party, "criterios": list(self.criteria)}


def correlate(prop: PropertyProfile, process: ProcessProfile) -> CorrelationResult:
    """Classifica a correlação determinística imóvel × processo.

    - ALTA: CPF ou CNPJ exato de uma parte coincide com o do proprietário conhecido.
    - MEDIA: nome compatível + comarca/UF compatível, sem identificador definitivo.
    - BAIXA: apenas nome semelhante (possível homônimo — não confirma identidade).
    - NAO_CONFIRMADA: dados insuficientes para qualquer correspondência.
    """
    owner_cpf = only_digits(prop.owner_cpf)
    owner_cnpj = only_digits(prop.owner_cnpj)

    # 1) Identificador exato → ALTA (único critério que confirma identidade).
    for party in process.parties:
        if owner_cpf and only_digits(party.cpf) and only_digits(party.cpf) == owner_cpf:
            return CorrelationResult(CORRELATION_HIGH, "CPF da parte coincide com o do proprietário conhecido.", party.name, ["cpf"])
        if owner_cnpj and only_digits(party.cnpj) and only_digits(party.cnpj) == owner_cnpj:
            return CorrelationResult(CORRELATION_HIGH, "CNPJ da parte coincide com o do proprietário conhecido.", party.name, ["cnpj"])

    # 2) Nome compatível (sem identificador). Avalia reforço por comarca/UF.
    name_match_party = None
    if prop.owner_name:
        for party in process.parties:
            if names_match(prop.owner_name, party.name):
                name_match_party = party
                break

    if name_match_party is not None:
        comarca_ok = _same_comarca(prop.comarca, process.comarca) or (
            bool(prop.city) and _same_comarca(prop.city, process.comarca)
        )
        uf_ok = bool(prop.state) and bool(process.uf) and normalize_name(prop.state) == normalize_name(process.uf)
        if comarca_ok or uf_ok:
            criterios = ["nome"] + (["comarca"] if comarca_ok else []) + (["uf"] if uf_ok else [])
            return CorrelationResult(
                CORRELATION_MEDIUM,
                "Nome compatível e localização (comarca/UF) compatível, sem identificador definitivo (CPF/CNPJ). Não confirma identidade.",
                name_match_party.name,
                criterios,
            )
        return CorrelationResult(
            CORRELATION_LOW,
            "Apenas nome semelhante, sem identificador nem localização compatível. Possível homônimo — não confirma identidade.",
            name_match_party.name,
            ["nome"],
        )

    # 3) Sem CPF/CNPJ e sem nome correspondente → dados insuficientes.
    return CorrelationResult(
        CORRELATION_UNCONFIRMED,
        "Dados insuficientes para correlacionar o processo ao proprietário/imóvel.",
        None,
        [],
    )


def parties_from_payload(parties: list[dict[str, Any]] | None) -> list[ProcessParty]:
    """Converte as partes do payload da Judicial API em ProcessParty."""
    result: list[ProcessParty] = []
    for p in parties or []:
        result.append(ProcessParty(
            name=p.get("name"),
            cpf=p.get("cpf") or p.get("document_cpf"),
            cnpj=p.get("cnpj") or p.get("document_cnpj"),
            role=p.get("role"),
        ))
    return result
