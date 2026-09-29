"""Transporte HTTP real para o DataJudProvider (TASK FINAL — Entrega 2).

Adapter fino sobre ``httpx`` que satisfaz o Protocol ``HttpTransport`` esperado
pelo ``DataJudProvider`` (``post(url, *, json, headers, timeout) -> HttpResponse``).

Mantém o provider agnóstico ao cliente HTTP concreto: o transporte é injetável, o
que preserva a testabilidade (os testes injetam um transporte falso) e permite a
consulta real ao DataJud em produção sem alterar o provider.

Nenhuma credencial é tratada aqui — a API key do DataJud é responsabilidade do
provider (header ``Authorization: APIKey <chave>``). Este módulo só transporta.
"""
from __future__ import annotations

import httpx


class HttpxTransport:
    """Implementação de ``HttpTransport`` baseada em ``httpx``.

    Reusa um único ``httpx.Client`` (com pool de conexões) por instância. O
    ``timeout`` é definido por requisição pelo provider (deriva do timeout por
    fonte), então não fixamos um timeout global aqui.
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()

    def post(self, url: str, *, json: dict, headers: dict, timeout: float) -> httpx.Response:
        return self._client.post(url, json=json, headers=headers, timeout=timeout)

    def close(self) -> None:
        self._client.close()
