"""Configuração externa do módulo Judicial API (JUR-01).

Toda configuração vem de variáveis de ambiente (prefixo JUDICIAL_) ou de um
arquivo .env, via pydantic-settings. NÃO há segredo hardcoded: credenciais do
provider (ex.: API key do DataJud) só existem se fornecidas por ambiente/secret,
e não são exigidas nesta fase (não há chamada real ao DataJud na JUR-01).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import SERVICE_NAME, __version__


class JudicialSettings(BaseSettings):
    """Configuração da Judicial API. Prefixo de ambiente: JUDICIAL_."""

    service_name: str = SERVICE_NAME
    version: str = __version__
    environment: str = "local"

    # Nível de log estruturado (DEBUG|INFO|WARNING|ERROR).
    log_level: str = "INFO"

    # Nome do header usado para propagar o correlation id de ponta a ponta.
    correlation_id_header: str = "X-Correlation-ID"

    # Timeouts padrão (ms). Valores base configuráveis; a aplicação real por
    # fonte/tribunal virá nas próximas tasks.
    default_source_timeout_ms: int = 8000
    global_timeout_ms: int = 60000

    # Base URL do DataJud (configurável; padrão = endpoint público oficial).
    datajud_base_url: str = "https://api-publica.datajud.cnj.jus.br"

    # Credencial do provider — OPCIONAL nesta fase. Nunca versionar segredo:
    # deve vir de ambiente/secret externo. Ausente por padrão. A chave do DataJud
    # é pública e pode mudar; por isso fica em configuração, nunca hardcoded.
    datajud_api_key: str | None = Field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Segurança da API (JUR-05, SPEC §73)
    # ------------------------------------------------------------------
    # Autenticação do CONSUMIDOR (distinta da credencial do DataJud). As chaves
    # nunca são versionadas: vêm de ambiente/secret. Formato: uma lista separada
    # por vírgula, onde cada item é "chave" (todos os escopos) ou "chave:escopo1|escopo2".
    # Ex.: JUDICIAL_API_KEYS="k-abc:search|read, k-ops:read"
    api_keys: str | None = Field(default=None, repr=False)
    # Header por onde o consumidor envia a API key.
    api_key_header: str = "X-API-Key"
    # Quando não há nenhuma chave configurada, a autenticação fica DESLIGADA
    # (modo local/dev). Em ambientes com chaves configuradas ela é obrigatória.
    # Este flag permite exigir auth mesmo sem chaves (falha fechada) se desejado.
    require_auth: bool = False

    # ------------------------------------------------------------------
    # Rate limiting HTTP (JUR-05, SPEC §73)
    # ------------------------------------------------------------------
    rate_limit_enabled: bool = True
    # Máximo de requisições por janela, por consumidor (API key ou IP de origem).
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # ------------------------------------------------------------------
    # Hardening (JUR-05, SPEC §73)
    # ------------------------------------------------------------------
    # Limite de tamanho do corpo da requisição (bytes) — protege contra payloads
    # abusivos. 0 desabilita a checagem.
    max_request_bytes: int = 1_048_576  # 1 MiB
    # Origens permitidas para CORS (lista separada por vírgula). Vazio = sem CORS.
    cors_allow_origins: str = ""

    model_config = SettingsConfigDict(
        env_prefix="JUDICIAL_",
        env_file=".env",
        extra="ignore",
    )

    @field_validator("api_key_header", "correlation_id_header")
    @classmethod
    def _non_empty_header(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("nome de header não pode ser vazio")
        return v

    @property
    def has_datajud_credential(self) -> bool:
        return bool(self.datajud_api_key)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    def parsed_api_keys(self) -> dict[str, frozenset[str]]:
        """Mapeia cada API key de consumidor para o conjunto de escopos concedidos.

        Escopo vazio/ausente => acesso total (conjunto vazio significa "sem
        restrição de escopo"). Segredos nunca são logados (SPEC §71, §73).
        """
        result: dict[str, frozenset[str]] = {}
        if not self.api_keys:
            return result
        for item in self.api_keys.split(","):
            item = item.strip()
            if not item:
                continue
            key, _, scopes_raw = item.partition(":")
            key = key.strip()
            if not key:
                continue
            scopes = frozenset(s.strip() for s in scopes_raw.split("|") if s.strip())
            result[key] = scopes
        return result

    @property
    def auth_enabled(self) -> bool:
        """Auth está ativa se há chaves configuradas OU se exigida explicitamente."""
        return self.require_auth or bool(self.parsed_api_keys())


@lru_cache
def get_settings() -> JudicialSettings:
    """Retorna as settings (cacheadas) da Judicial API."""
    return JudicialSettings()
