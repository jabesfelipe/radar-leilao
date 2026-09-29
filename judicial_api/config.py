"""Configuração externa do módulo Judicial API (JUR-01).

Toda configuração vem de variáveis de ambiente (prefixo JUDICIAL_) ou de um
arquivo .env, via pydantic-settings. NÃO há segredo hardcoded: credenciais do
provider (ex.: API key do DataJud) só existem se fornecidas por ambiente/secret,
e não são exigidas nesta fase (não há chamada real ao DataJud na JUR-01).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
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

    model_config = SettingsConfigDict(
        env_prefix="JUDICIAL_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def has_datajud_credential(self) -> bool:
        return bool(self.datajud_api_key)


@lru_cache
def get_settings() -> JudicialSettings:
    """Retorna as settings (cacheadas) da Judicial API."""
    return JudicialSettings()
