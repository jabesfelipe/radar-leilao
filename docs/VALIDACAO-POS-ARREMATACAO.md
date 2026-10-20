# Validação de integração e consistência — Pós-Arrematação (imóvel 633)

Data: 20/09/2026. Objetivo: diagnosticar os 3 problemas observados nas capturas,
documentar as regras de negócio, validar o ciclo CRUD/persistência/linha do tempo em
ambiente isolado e aplicar as correções mínimas. Nenhuma análise LLM nova, nenhuma
nova versão de análise do 633, nenhum histórico apagado.

## Dados reais do 633 (banco, inalterados)

| Campo | Valor |
|---|---|
| post_auction.status | EM_ANDAMENTO |
| post_auction.eviction_mode | NULL (indefinida) |
| post_auction.initial_budget | R$ 444.417,96 |
| post_auction.expected_sale_value | R$ 300.000,00 |
| post_auction_costs | 0 registros |
| etapas | 16 (todas PENDENTE) |
| análises | 9 (V1–V9), sem V10 |

## Problema 1 — status EM_ANDAMENTO com etapas PENDENTE e modalidade indefinida

**Diagnóstico: comportamento esperado, não é bug.** Na ativação sob demanda, o
registro nasce `status=EM_ANDAMENTO`, as 16 etapas padrão são semeadas em `PENDENTE`
e `eviction_mode=NULL` até o usuário escolher PRÓPRIA/TERCEIRIZADA. O que faltava era
documentar a regra.

### Regra de status (documentada)
- **Fluxo não iniciado**: não existe registro `post_auctions`. A visão geral retorna
  `ativado=false` e a UI mostra o CTA de ativação. O imóvel segue o fluxo normal.
- **Ativado**: `EM_ANDAMENTO` (padrão na ativação). Etapas iniciam `PENDENTE`.
- **Transições de etapa**: `PENDENTE → EM_ANDAMENTO → CONCLUIDA`; `NAO_APLICAVEL`
  quando a etapa não se aplica ao imóvel; `BLOQUEADA` quando há impedimento. Nem toda
  etapa é obrigatória.
- **Conclusão**: `CONCLUIDO` (ao encerrar; grava `closed_at`). `CANCELADO` quando o
  investimento é abortado. Modalidade `eviction_mode` é opcional e só deixa de ser
  "indefinida" por decisão explícita.

## Problema 2 — orçamento inicial e custo acumulado de R$ 444.417,96, porém previsto/pago/pendente = 0

**Diagnóstico: correto por design; era um problema de CLAREZA, não de cálculo.**

Distinção documentada e agora explícita na UI:
- **Orçamento inicial (herdado da análise)**: snapshot do custo total determinístico
  da análise (`build_finance.custo_total`), congelado na ativação. É referência, não
  gasto realizado.
- **Total previsto na execução**: soma dos `planned_amount` dos custos pós-arrematação
  (tabela própria). Zero enquanto nada é cadastrado.
- **Total pago (realizado)**: soma dos `actual_amount` dos itens `PAGO`.
- **Compromissos pendentes**: o que falta pagar (previsto − realizado) dos itens não
  pagos.
- **Custo total acumulado** = orçamento inicial + realizado pós-arrematação.

No 633, sem custos de execução, previsto/pago/pendente = 0 e o custo acumulado =
orçamento inicial (444.417,96). A UI passou a separar visualmente "Orçamento herdado
da análise", "Execução" e "Consolidado", com nota explicativa.

## Problema 3 — ROI −32,5% no Pós-Arrematação x −35,87% no Financeiro (DIVERGÊNCIA CONFIRMADA)

**Causa raiz:** os denominadores eram IGUAIS (custo total 444.417,96); a diferença
estava no **numerador**:

| Tela | Fórmula | Memória (633) | ROI |
|---|---|---|---|
| Financeiro | `roi_operacao = (V − custo_saida − custo_total) / custo_total` | (300.000 − 15.000 − 444.417,96) / 444.417,96 | −0,35871 |
| Pós (antes) | `roi = (V − custo_acumulado) / custo_acumulado` | (300.000 − 444.417,96) / 444.417,96 | −0,32496 |

O Pós **ignorava o custo de saída** (corretagem/tributo da venda = R$ 15.000) no lucro,
produzindo dois ROIs diferentes para o mesmo imóvel.

### Correção mínima (regra de negócio: um único conceito de resultado)
`post_auction_cost_summary` passou a calcular o lucro com a MESMA definição do
Financeiro (resultado líquido = venda − custo de saída − custo acumulado), lendo o
`custo_saida` de `build_finance` (não recalcula; `build_finance` permanece intacto).
Também passou a expor `custo_saida_estimado` para transparência.

Resultado pós-correção (633, ao vivo): Pós `roi_estimado = −0,35871` ==
Financeiro `roi_operacao = −0,35871`. Quando houver custos de execução pagos, o custo
acumulado cresce e o ROI do Pós evolui, mantendo a mesma definição de resultado.

Nenhuma fórmula do motor financeiro da análise (`build_finance`/`calculate_financial`)
foi alterada.

## Validação do ciclo (ambiente ISOLADO — imóvel de teste, nunca o 633)

Imóvel de teste criado via API, exercitado e removido (0 resíduos):
- custo PREVISTO (previsto=3.000, pendente=3.000) e custo PAGO (realizado) — consolidação
  correta (previsto=8.000, realizado=4.800, pendente=3.000, variação=−3.200);
- edição do custo pago (realizado=5.100 → custo acumulado=205.100);
- contato + tentativa; consultoria + proposta; minuta + versão (v2 REVISADO);
- **recarga** da visão geral: tudo persistido (2 custos, 1 contato, 1 consultoria, 1
  minuta, 16 etapas);
- **linha do tempo**: eventos `POS_ARREMATACAO_ATIVADA`, `POS_CUSTO_ADICIONADO`,
  `POS_CONTATO_ADICIONADO`, `POS_CONSULTORIA_ADICIONADA`, `POS_NOTIFICACAO_CRIADA`
  presentes no `/historico` (integração confirmada);
- **persistência pós-reinicialização**: após `docker compose build` + `up -d`, o
  pós-arrematação do 633 permanece (16 etapas, EM_ANDAMENTO) e o ROI corrigido é
  servido pela aplicação em execução.

## Testes automatizados (resultados reais)

- Backend: suíte completa **passando** (inclui novo teste
  `test_roi_pos_consistente_com_financeiro_sem_custos_execucao`, que trava a regra de
  consistência de ROI).
- Frontend: `tsc --noEmit` sem erros + `vitest run` passando.
- Imóvel 633 intacto: 9 análises (V1–V9), zero V10; nenhuma análise nova.

## Arquivos alterados

- `backend/app/services.py` — `post_auction_cost_summary`: lucro/ROI alinhados ao
  Financeiro (custo de saída incluído) + `custo_saida_estimado` exposto.
- `frontend/src/services/postAuction.ts` — tipo `PostAuctionSummary.custo_saida_estimado`.
- `frontend/src/pages/PostAuctionSection.tsx` — resumo separado em "Orçamento herdado",
  "Execução" e "Consolidado" + nota explicativa.
- `tests/test_pos_arrematacao.py` — teste de consistência de ROI.
- `docs/VALIDACAO-POS-ARREMATACAO.md` — este relatório.
