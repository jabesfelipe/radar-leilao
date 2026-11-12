# Jurídico e Central Jurídica

**Status: implementado** (consulta judicial por DataJud depende de `judicial_api/` e de credenciais; Registro de Imóveis e Prefeitura sem cliente).

## Objetivo
Registrar processos e movimentações, correlacioná-los ao imóvel, consultar a Judicial API e oferecer uma biblioteca jurídica (fontes, dispositivos, regras) que embasa o checklist.

## Funcionalidades
- Processos do imóvel: cadastro, edição cadastral com histórico, movimentações **append-only**.
- Consulta à Judicial API (DataJud) com persistência de processos e sinais; vínculo/validação manual de processo; correlação do processo com o imóvel (o hard stop `ACAO_ANULATORIA_ATIVA` usa correlação ALTA).
- Riscos jurídicos persistidos (categoria `juridico`).
- **Central Jurídica**: `legal_catalog.py` com 5 fontes, 11 dispositivos e 8 regras (Lei 9.514 arts. 26, 27 e 37-A; Código Civil arts. 1.228 e 447; CPC art. 903; Lei 8.245 art. 8º; CTN arts. 130 e 131). Busca vetorial quando há embeddings, textual caso contrário.
- Referências jurídicas por item do checklist (`canonical_key`) e por contexto (ex.: DESOCUPACAO, LEILAO).

## Telas
Hub `/juridico`; no imóvel: "Jurídico (Processos)" e "Central Jurídica".

## Endpoints
`/api/imoveis/{id}/processos` (GET/POST), `PATCH .../{pid}`, `POST .../{pid}/movimentacoes`, `POST /api/imoveis/{id}/processos/consultar`, `POST /api/imoveis/{id}/juridico/processos/{pid}/vincular`, `GET /api/imoveis/{id}/juridico/riscos`, `GET /api/imoveis/{id}/juridico/central`;
`/api/juridico/biblioteca`, `/api/juridico/biblioteca/busca`, `/api/juridico/referencias/checklist/{canonical_key}`, `/api/juridico/referencias/contexto/{contexto}`; hub `GET /api/juridico`.

## Integrações
Judicial API própria (`POST {JUDICIAL_API_BASE_URL}/api/v1/judicial/search`, cabeçalho `X-API-Key`, padrão `http://judicial_api:8010`) sobre DataJud. Ver [integrations](../../03-architecture/integrations.md).

## Regras
A Central Jurídica é apoio à análise, não parecer jurídico. Usufruto: óbito alegado não basta; exige cancelamento na matrícula (hard stop `USUFRUTO_NAO_EXTINTO`).

## Limitações
Os 11 dispositivos e 8 regras são o catálogo atual; curadoria pendente em [TODO-CENTRAL-JURIDICA](../specs/TODO-CENTRAL-JURIDICA.md). Comentário em `backend/app/legal_catalog.py` cita o caminho antigo `TODO-CENTRAL-JURIDICA` (ver [99-archive](../../99-archive/README.md)).

## Código
`legal_catalog.py`, `legal_service.py`, `legal_correlation.py`, `judicial_client.py`, `judicial_integration.py`, `routers/legal_central.py`, `judicial_api/`. Specs: [CENTRAL-JURIDICA](../specs/CENTRAL-JURIDICA.md), [MATRIZ-CURADORIA-JURIDICA](../specs/MATRIZ-CURADORIA-JURIDICA.md), [JUDICIAL-API-SPEC](../../03-architecture/specs/JUDICIAL-API-SPEC.md).
