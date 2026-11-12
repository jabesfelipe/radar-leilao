# Imóveis e cadastro

**Status: implementado.**

## Objetivo
Cadastrar e manter o imóvel, o leilão, o edital, a matrícula e as fontes, com histórico de alterações.

## Funcionalidades
- Cadastro simples e **cadastro completo transacional** (imóvel, leilão, edital, matrícula e fontes).
- Edição de dados cadastrais com histórico antes/depois e evento de domínio.
- Fontes do imóvel (página, edital, matrícula, outra) com histórico.
- Matrícula e edital: criação, listagem (atual e histórico) e edição de metadados.
- Custos e premissas do imóvel (ver [financial-debts.md](financial-debts.md)).

## Telas
`/imoveis` (listagem) e `/imoveis/{id}` (PropertyDetailPage). Seções: visão-geral, cadastro, leilão, documentos, matrícula, edital, jurídico (Processos), central-jurídica, financeiro, débitos, mercado, ocupação, checklist, riscos, veredito, due-diligence, pós-arrematação, histórico. Uma seção sem componente mostra o placeholder "MÓDULO EM PREPARAÇÃO".

## Endpoints (`main.py`, sem JWT)
`GET/POST /api/imoveis`; `PATCH /api/imoveis/{id}`; `POST /api/imoveis/completo`; `GET/POST /api/imoveis/{id}/fontes` (+ `/fontes/historico`, `PATCH`/`DELETE /fontes/{sid}`); `GET/POST /api/imoveis/{id}/matricula` e `PATCH .../{rid}`; `GET/POST /api/imoveis/{id}/edital` e `PATCH .../{nid}`; `GET /api/imoveis-resumo`.

## Dados
`Property`, `Auction`, `AuctionNotice`, registro de matrícula, `PropertySource`, `EntityHistory`, eventos de domínio.

## Regras
Dado cadastral editável com histórico; análises e documentos são versionados e não sobrescritos. O imóvel 633 (COND PARQUE ARVOREDO RESIDENCIAL CLUBE) é o imóvel de referência protegido.

## Permissões
Backend sem JWT nessas rotas (legado); portão do proxy na borda.

## Código
`backend/app/main.py` (rotas), `models.py`, `schemas.py`; `frontend/src/pages` (PropertyDetailPage e seções), `frontend/src/services` (properties, registration).
