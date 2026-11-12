# Leiloeiros

**Status: implementado.**

## Objetivo
Cadastrar leiloeiros, seus portais de acesso e documentos, e associá-los ao leilão do imóvel.

## Funcionalidades
- CRUD de leiloeiros com histórico de alterações (sem segredos).
- Portais de acesso por leiloeiro; credenciais **cifradas** (Fernet, `PORTAL_SECRET_KEY`); o histórico guarda apenas `has_secret`.
- Recuperação de credencial em endpoint dedicado, protegido por `X-Portal-Admin-Token` (`PORTAL_ADMIN_TOKEN`) e auditável.
- Documentos do leiloeiro (metadados).
- Vínculo do leiloeiro ao leilão corrente do imóvel, preservando o texto histórico.

## Telas
`/leiloeiros` (AuctioneersPage).

## Endpoints
`/api/leiloeiros` (GET, POST), `/{id}` (GET, PATCH, DELETE), `/{id}/historico`, `/{id}/portais` (POST, PATCH, DELETE), `/{id}/portais/{pid}/credencial` (GET), `/{id}/documentos` (POST, PATCH, DELETE); `POST /api/imoveis/{id}/leilao/leiloeiro`.

## Permissões
Rotas sem JWT no backend (legado); o segredo é protegido pelo token dedicado e pelo portão do proxy.

## Limitações
Nenhuma integração automática com portais; a lista de portais candidatos está em [REVISAO-ANOTACOES-LEILAO](../specs/REVISAO-ANOTACOES-LEILAO.md).

## Código
`main.py`, `secrets_crypto.py`, `models.py`; frontend `AuctioneersPage` e serviço `auctioneers`.
