# Auditoria final do PR #11 (20/11/2026)

Escopo: diff completo de `feat/inteligencia-completa` (PR #10 incluído), E2E local, segurança da pesquisa externa, migration
`0027` e revalidação somente leitura do imóvel 7. Sem merge, deploy, tag ou alteração de produção.

## Problemas encontrados e corrigidos

| # | Problema | Impacto | Correção |
|---|---|---|---|
| 1 | `POST /pesquisa-automatica` caía na política genérica de escrita, sem limite por minuto nem de concorrência | Chamadas repetidas consumiriam crédito pago da API de pesquisa | Rota classificada como operação crítica (`security.py`) |
| 2 | Cache da pesquisa por texto da consulta, sem o imóvel | Dois imóveis com a mesma consulta compartilhavam o registro; o segundo não via a consulta no histórico | Imóvel entra na chave do cache (`search/service.py`) |
| 3 | Nova tentativa imediata em 429/5xx | Repetir sem espera tende a receber 429 de novo | Espera crescente configurável (`SEARCH_RETRY_BACKOFF_SECONDS`) |
| 4 | IPTU do Resumo somava os débitos sem a regra de duplicidade do Financeiro e ignorava débito com status PENDENTE | Consulta registrada duas vezes dobrava o valor no Resumo, diferente do Financeiro | Mesmo critério do Financeiro (`is_real_debt` + `dedupe_debts`); aviso quando a consulta mais recente não acha débito mas há débito anterior |
| 5 | Tabelas novas (cenários, comparáveis, documentos esperados) sem contêiner de rolagem | Estouro horizontal em celular | `hub-table-wrap`, padrão do projeto |
| 6 | FK `external_searches.property_id` sem regra de exclusão | Excluir um imóvel pesquisado falharia por FK | `ON DELETE CASCADE` (a pesquisa é cache do imóvel) |
| 7 | E2E sem a aba "Resumo do investimento" e sem o fluxo da inteligência | Evolução sem cobertura de ponta a ponta | Aba incluída em `mobile-detalhe.spec.ts`; nova suíte `inteligencia.spec.ts` |

## E2E local

Ambiente: backend em banco descartável `radar_e2e`, sem chave de IA nem de pesquisa; frontend Vite local.

- `inteligencia.spec.ts` (novo): 2/2.
- `fluxo.spec.ts` e `correcoes.spec.ts:32`: verdes. Falhas da primeira execução eram do ambiente (o backend lia uma chave de
  IA do `.env` local).
- Falhas restantes, idênticas na `main` (`e134cc7`) no mesmo ambiente (172 passed, 16 failed), portanto **anteriores** ao PR:
  `correcoes.spec.ts:97`, `correcoes.spec.ts:193` (6 viewports), `mobile-detalhe.spec.ts:76` (6 viewports) e
  `mobile.spec.ts:113` `/historico` (3 viewports). Causas vistas a 360px: campos do Financeiro e tabelas de cenários/preço
  máximo do Mercado mais largos que a tela, e itens da linha do tempo do histórico com código interno longo. Os componentes
  envolvidos não foram alterados por este PR.

## Verificado sem problema

- Chaves de API: lidas só do ambiente; enviadas em cabeçalho (nunca na URL); não registradas em log, banco, resposta ou commit.
- Sem provedor: `NAO_CONFIGURADO`, nada gravado; erro de pesquisa na análise fica num savepoint e só é registrado em log.
- Mesmo valor de venda e taxa de condomínio em Resumo, Mercado e Financeiro (teste de API e E2E).
- Riscos sem duplicidade e sem códigos internos; desconhecido continua `null`/"Desconhecido".
- Migration `0027`: só cria tabela e índices (`IF NOT EXISTS`), não toca dados existentes; `downgrade` remove a tabela; imagem
  v1.0.13 continua compatível com o banco migrado (tabela sem uso).
