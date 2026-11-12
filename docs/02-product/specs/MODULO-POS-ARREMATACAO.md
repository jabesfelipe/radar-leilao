# Módulo Pós-Arrematação

Acompanha a execução real do investimento após a arrematação — do pagamento e
regularização documental à desocupação, eventual ação judicial, reforma e
preparação para venda/locação. Vinculado ao imóvel e ao leilão existentes; não é
uma aplicação separada e não duplica o cadastro do imóvel.

## Ativação sob demanda

O módulo só existe quando o imóvel entra no fluxo de execução. Imóveis apenas
analisados seguem o fluxo atual normalmente (o endpoint de visão geral retorna
`ativado=false` e a UI exibe um CTA de ativação). A ativação congela o orçamento
inicial a partir do custo total determinístico da análise (`build_finance`) — sem
sobrescrever a análise.

- `POST /api/imoveis/{id}/pos-arrematacao/ativar` — idempotente; semeia as 16 etapas padrão.
- `GET /api/imoveis/{id}/pos-arrematacao` — visão consolidada (estado, etapas, custos, contatos, consultorias, minutas, resumo financeiro + financeiro da análise).
- `PATCH /api/imoveis/{id}/pos-arrematacao` — estado/modalidade/orçamento.

## Reuso (não duplica domínios)

- **Linha do tempo**: todas as mutações emitem `DomainEvent` + `EntityHistory` e
  aparecem no endpoint `/historico` e na aba Histórico existentes. Novos tipos:
  `POS_ARREMATACAO_ATIVADA/ATUALIZADA`, `POS_ETAPA_*`, `POS_CUSTO_*`,
  `POS_CONTATO_*`, `POS_CONSULTORIA_*`, `POS_NOTIFICACAO_*`.
- **Ação judicial**: a etapa de imissão referencia `legal_processes` via
  `legal_process_id` — reusa o domínio de Processos Jurídicos, sem cadastro duplicado.
- **Desocupação (estado)**: continua em `OccupancyAnalysis` (`/ocupacao`).
- **Financeiro da análise**: `build_finance`/`Cost` permanecem a fonte da análise
  inicial e NÃO são sobrescritos. O custo pós-arrematação é uma tabela própria com
  semântica previsto/realizado/pago.

## Entidades (migration 0015_pos_arrematacao)

| Tabela | Finalidade |
|---|---|
| `post_auctions` | Estado/ativação do fluxo (1 por imóvel): status, modalidade de desocupação, orçamento inicial congelado, valor de venda estimado. |
| `post_auction_stages` | 16 etapas configuráveis: prevista/efetiva, responsável, situação, obs, link opcional a processo jurídico. Cada etapa pode ser `NAO_APLICAVEL`. |
| `post_auction_costs` | Custos com **previsto/realizado/pago**, situação (PREVISTO/PENDENTE/PAGO/CANCELADO/CONTESTADO), competência/pagamento, fornecedor, forma de pagamento, origem, vínculo à etapa, comprovante (document_version). |
| `occupant_contacts` + `contact_attempts` | Contatos do ocupante (sem presumir condição jurídica) e histórico de tentativas (canal, resultado, próxima ação). |
| `consultancies` + `consultancy_proposals` | Consultoria de desocupação terceirizada e propostas comparáveis (honorários fixos/variáveis, escopo incluso/à parte). |
| `notification_drafts` + `notification_draft_versions` | Minutas de notificação extrajudicial editáveis e versionadas (rascunho→revisado→emitido→enviado→recebido), com registro de envio/recebimento quando houver comprovação. |

## Financeiro consolidado (determinístico, sem LLM)

`post_auction_cost_summary` preserva a distinção ESTIMATIVA × OBRIGAÇÃO × PAGO:

- `previsto_total` = soma dos previstos (exceto CANCELADO);
- `realizado_total` = soma dos realizados dos itens PAGOS;
- `pendente_total` = o que falta pagar dos itens não pagos;
- `variacao_previsto_realizado` = realizado − previsto;
- `custo_total_acumulado` = orçamento inicial congelado + realizado pós-arrematação;
- `lucro_estimado`/`roi_estimado` quando há valor de venda estimado.

Nunca sobrescreve o financeiro histórico da análise.

## Limites de escopo (não implementado nesta etapa)

Integrações pagas, disparo automático de notificações, assinaturas eletrônicas e
automações externas estão fora de escopo. As minutas são documentos editáveis, não
pareceres jurídicos — o sistema não afirma validade jurídica, recebimento ou
cumprimento de prazo sem comprovação.

## Frontend

Nova aba **Pós-Arrematação** no dossiê (`PropertyDetailPage`), componente
`PostAuctionSection` consumindo `services/postAuction.ts`. Quando inativo, exibe o
CTA de ativação; quando ativo, mostra situação, resumo financeiro consolidado,
etapas, custos (previsto/realizado/situação), contatos, consultorias e minutas.

## Testes

- Backend: `tests/test_pos_arrematacao.py` (11 testes) — ativação sob demanda,
  custos previsto/pago/pendente sem duplicidade, não sobrescrita do financeiro da
  análise, contatos+tentativas, minuta versionada, consultoria+propostas, etapa
  reusando LegalProcess, eventos na linha do tempo e histórico before/after.
- Frontend: `PostAuctionSection.test.tsx` (5 testes) — CTA de ativação, ativação,
  resumo consolidado, criação de custo e tratamento de erro.
