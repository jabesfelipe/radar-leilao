"""Loader do catálogo de fontes judiciais (JUR-02).

Lê ``tribunals.json`` (fonte de verdade) uma única vez e o transforma em
entradas de catálogo (``CatalogEntry``). Toda a lógica é genérica e dirigida por
dados: adicionar/alterar um tribunal é editar o JSON, não escrever código novo.

Regra de capacidades (SPEC §3): as capacidades vêm do ``default_capabilities`` do
catálogo, com override opcional por tribunal via chave ``supports``. Nunca
assumir um critério não comprovado — o padrão marca name/cpf/cnpj como falso.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..enums import JusticeType
from ..models import SearchCriteriaSupport, TribunalCapabilities, TribunalInfo

_CATALOG_FILE = Path(__file__).with_name("tribunals.json")


def build_search_url(base_url: str, alias: str) -> str:
    """Monta a URL de busca do DataJud para um alias (SPEC/doc oficial):
    ``<base_url>/api_publica_<alias>/_search``.
    """
    return f"{base_url.rstrip('/')}/api_publica_{alias}/_search"


@dataclass(frozen=True)
class CatalogEntry:
    """Uma fonte do catálogo: identidade + endpoint + capacidades.

    ``search_url`` já resolve o endpoint específico do DataJud, mantendo o resto
    do sistema alheio a aliases/URLs (encapsulamento — SPEC §26, §76-77).
    """

    code: str
    name: str
    justice_type: JusticeType
    uf: str | None
    alias: str
    aliases: tuple[str, ...]
    search_url: str
    capabilities: SearchCriteriaSupport
    enabled: bool = True

    def to_info(self) -> TribunalInfo:
        return TribunalInfo(
            code=self.code,
            name=self.name,
            justice_type=self.justice_type,
            uf=self.uf,
            enabled=self.enabled,
        )

    def to_capabilities(self) -> TribunalCapabilities:
        return TribunalCapabilities(tribunal=self.code, supports=self.capabilities)


class JudicialCatalog:
    """Coleção imutável de fontes, indexada por código e por alias textual."""

    def __init__(self, provider: str, base_url: str, entries: list[CatalogEntry]) -> None:
        self.provider = provider
        self.base_url = base_url
        self._entries = list(entries)
        self._by_code = {e.code: e for e in entries}
        # Índice de aliases textuais -> código canônico (case-insensitive).
        self._alias_index: dict[str, str] = {}
        for e in entries:
            self._alias_index[e.code.lower()] = e.code
            self._alias_index[e.alias.lower()] = e.code
            for extra in e.aliases:
                self._alias_index[extra.lower()] = e.code

    def entries(self) -> list[CatalogEntry]:
        return list(self._entries)

    def codes(self) -> list[str]:
        return [e.code for e in self._entries]

    def get(self, code: str) -> CatalogEntry | None:
        return self._by_code.get(code)

    def resolve_alias(self, alias: str) -> str | None:
        if not alias:
            return None
        return self._alias_index.get(alias.strip().lower())

    def for_justice_types(self, justice_types: list[JusticeType]) -> list[CatalogEntry]:
        if not justice_types:
            return self.entries()
        wanted = set(justice_types)
        return [e for e in self._entries if e.justice_type in wanted]


def _merge_capabilities(defaults: dict, override: dict | None) -> SearchCriteriaSupport:
    merged = dict(defaults or {})
    if override:
        merged.update(override)
    # 'class' é palavra reservada em Python; o modelo expõe alias 'class'.
    return SearchCriteriaSupport(
        name=bool(merged.get("name", False)),
        cpf=bool(merged.get("cpf", False)),
        cnpj=bool(merged.get("cnpj", False)),
        process_number=bool(merged.get("process_number", False)),
        subject=bool(merged.get("subject", False)),
        court=bool(merged.get("court", False)),
        movements=bool(merged.get("movements", False)),
        **{"class": bool(merged.get("class", False))},
    )


def _parse(data: dict, base_url_override: str | None) -> JudicialCatalog:
    provider = data.get("provider", "DATAJUD")
    base_url = base_url_override or data.get("base_url", "")
    defaults = data.get("default_capabilities", {})
    entries: list[CatalogEntry] = []
    for raw in data.get("tribunals", []):
        alias = raw["alias"]
        entries.append(
            CatalogEntry(
                code=raw["code"],
                name=raw["name"],
                justice_type=JusticeType(raw["justice_type"]),
                uf=raw.get("uf"),
                alias=alias,
                aliases=tuple(raw.get("aliases", [])),
                search_url=build_search_url(base_url, alias),
                capabilities=_merge_capabilities(defaults, raw.get("supports")),
                enabled=bool(raw.get("enabled", True)),
            )
        )
    return JudicialCatalog(provider=provider, base_url=base_url, entries=entries)


def load_catalog(path: Path | None = None, base_url_override: str | None = None) -> JudicialCatalog:
    """Carrega o catálogo do arquivo JSON. ``path`` e ``base_url_override`` são
    úteis para testes/configuração externa."""
    target = path or _CATALOG_FILE
    data = json.loads(target.read_text(encoding="utf-8"))
    return _parse(data, base_url_override)


@lru_cache
def default_catalog() -> JudicialCatalog:
    """Catálogo padrão (cacheado) a partir do arquivo versionado."""
    return load_catalog()
