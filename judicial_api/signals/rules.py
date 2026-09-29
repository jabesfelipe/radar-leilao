"""Catálogo de regras de sinais jurídicos (JUR-04).

Regras VERSIONADAS carregadas de ``signal_rules.json`` (fonte de verdade em
dados). Cada regra detecta uma evidência por correspondência de termos
(normalizados sem acento/caixa) em movimentos/assuntos/classe (SPEC §37-38).
Adicionar/alterar uma regra é editar o JSON — não escrever código novo.
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..enums import SignalCategory, SignalSeverity

_RULES_FILE = Path(__file__).with_name("signal_rules.json")


def normalize_text(value: str | None) -> str:
    """Minúsculas + sem acentos, para casar termos de forma robusta."""
    base = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return base.lower().strip()


@dataclass(frozen=True)
class SignalRule:
    signal_code: str
    name: str
    category: SignalCategory
    severity: SignalSeverity
    base_confidence: float
    terms: tuple[str, ...]          # termos já normalizados
    version: int = 1
    enabled: bool = True

    def matches(self, normalized_text: str) -> bool:
        """True se algum termo da regra aparece no texto (já normalizado)."""
        return any(term and term in normalized_text for term in self.terms)


def _parse(data: dict) -> list[SignalRule]:
    rules: list[SignalRule] = []
    for raw in data.get("rules", []):
        if not raw.get("enabled", True):
            continue
        rules.append(
            SignalRule(
                signal_code=raw["signal_code"],
                name=raw.get("name", raw["signal_code"]),
                category=SignalCategory(raw["category"]),
                severity=SignalSeverity(raw["severity"]),
                base_confidence=float(raw.get("base_confidence", 0.5)),
                terms=tuple(normalize_text(t) for t in raw.get("terms", [])),
                version=int(raw.get("version", 1)),
                enabled=bool(raw.get("enabled", True)),
            )
        )
    return rules


def load_signal_rules(path: Path | None = None) -> list[SignalRule]:
    """Carrega as regras de um arquivo JSON (parametrizável para testes)."""
    target = path or _RULES_FILE
    data = json.loads(target.read_text(encoding="utf-8"))
    return _parse(data)


@lru_cache
def default_signal_rules() -> tuple[SignalRule, ...]:
    """Regras padrão (cacheadas) a partir do arquivo versionado."""
    return tuple(load_signal_rules())
