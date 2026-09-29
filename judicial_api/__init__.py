"""Judicial API — módulo independente de pesquisa processual judicial.

Este pacote é intencionalmente autocontido: não importa nada do Radar Leilão.
JUR-01 entrega apenas a fundação técnica (estrutura, config, app REST, health
check, contrato de erro, correlation id, logging estruturado, interfaces base de
Provider/Registry, DTOs e enums). Integração real com o DataJud, tribunais,
persistência completa, sinais, retry, paginação e concorrência ficam para as
tasks seguintes (JUR-02..JUR-05).
"""

__version__ = "0.1.0"
SERVICE_NAME = "judicial-api"
