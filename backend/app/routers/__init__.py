"""Pacote de routers da API do Radar Leilão (M0 — modularização).

Cada módulo expõe um ``router = APIRouter()`` com as MESMAS rotas (path, método,
response_model, status) que viviam em ``main.py``. O objetivo do M0 é organizar a
API em routers por domínio SEM alterar nenhum contrato — a verificação é feita por
``tests/contract/test_openapi_contract.py`` (diff contra ``openapi_baseline.json``).

Os routers são montados em ``main.py`` via ``app.include_router(...)``.
"""
