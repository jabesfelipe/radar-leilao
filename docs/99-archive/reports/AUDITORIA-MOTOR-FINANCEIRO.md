# Auditoria do Motor Financeiro — Imóvel 633 (Parque Arvoredo Residencial Clube)

Data: 2026-09-20. Escopo: validar custo total, custo de saída, resultado líquido,
margem, ROI, break-even e preço máximo de arrematação; identificar divergências e
corrigir somente o necessário. Sem nova análise LLM, sem alterar dados históricos
do imóvel 633.

## 1. Onde os números são calculados

- Motor determinístico: `backend/app/finance.py` → `calculate_financial()`.
- Único wrapper de produção: `backend/app/services.py` → `build_finance(prop)`, que
  monta as entradas a partir do banco:
  - `bid` = `Auction.acquisition_value` se preenchido, senão `Auction.bid_value`.
  - `costs` = lista `{category, amount}` de `prop.costs`.
  - `debts` = lista `{amount, status}` de `prop.debts` (somados se status != QUITADO).
  - Premissas de venda/meta = `Auction.financial_assumptions` (JSON), mapeadas por
    `_build_finance_assumptions()` para `SaleAssumptions` e `MaxPriceGoal`.
- Endpoint: `GET /api/imoveis/{id}/financeiro` recomputa AO VIVO (`build_finance`);
  `financial_analyses` guarda apenas o histórico versionado em `outputs`.
- Frontend: `frontend/src/pages/FinancialSection.tsx` apenas exibe os campos.

## 2. Dados reais persistidos do imóvel 633 (fonte: banco)

| Entrada | Valor |
|---|---|
| Lance (Auction.bid_value; acquisition_value = NULL) | R$ 222.000,00 |
| Avaliação (appraisal_value) | R$ 370.000,00 |
| Custo cadastrado: ITBI | R$ 8.000,00 |
| Custo cadastrado: Registro | R$ 3.000,00 |
| Custo cadastrado: "Comissão do arrematante" | R$ 11.000,00 |
| Custo cadastrado: "Condomínio em débito" | R$ 178.172,41 |
| Custo cadastrado: "IPTU em débito" | R$ 22.245,55 |
| Tabela `debts` | VAZIA (0 linhas) |
| Premissa: valor de venda estimado (V) | R$ 300.000,00 |
| Premissa: meta | MARGEM_MINIMA = 0,20 |
| Premissa: corretagem | 0,05 (5%) |
| Premissa: tributo na venda | 0 |
| Premissa: base do tributo | GANHO |
| Premissa: prazo | 12 meses |
| Premissa: carregamento mensal | R$ 0,00 |

Observação: o lance de R$ 222.000 NÃO é hardcoded no motor — é a coluna
`Auction.bid_value` persistida no cadastro do leilão.

## 3. Fórmulas (atuais = esperadas) e memória de cálculo

Notação: A = lance; comissão; F = demais custos fixos; CT = custo total;
V = valor de venda; c = corretagem (fração); t = tributo (fração).

### 3.1 Custo total
`CT = soma de todas as chaves do breakdown` (arrematação + comissão + ITBI +
registro + condomínio + IPTU + débitos + jurídicos + desocupação + reforma +
carregamento + outros). Cada custo é somado **uma única vez**.

Memória 633: 222.000 + 11.000 + 8.000 + 3.000 + 178.172,41 + 22.245,55 =
**R$ 444.417,96**. ✔ confere com o exibido.

### 3.2 Custo de saída
`custo_saida = V·c + tributos`, com `tributos = t·(V−CT)` (base GANHO) ou `t·V`
(base VENDA). Memória 633: 300.000·0,05 + 0 = **R$ 15.000,00**. ✔

### 3.3 Resultado líquido
`resultado_liquido = V − custo_saida − CT`.
Memória 633: 300.000 − 15.000 − 444.417,96 = **−R$ 159.417,96**. ✔

### 3.4 Margem líquida e ROI da operação
`margem_liquida = resultado_liquido / V`; `roi_operacao = resultado_liquido / CT`.
Memória 633: −159.417,96 / 300.000 = **−0,53139**; −159.417,96 / 444.417,96 =
**−0,35871**. ✔

### 3.5 Break-even (preço mínimo de saída para resultado zero)
Base GANHO: `V* = CT·(1−t) / (1−c−t)`; base VENDA: `V* = CT / (1−c−t)`.
Memória 633: 444.417,96·(1−0) / (1−0,05−0) = 444.417,96 / 0,95 =
**R$ 467.808,38**. ✔

### 3.6 Preço máximo de arrematação (meta MARGEM_MINIMA, base GANHO, t=0)
Meta de margem é **sobre a venda**: alvo = `meta·V`. Como t=0:
`A_max = (V − V·c − meta·V − F) / k`, com `k = 1` (sem comissão percentual) e
F já incluindo a comissão fixa cadastrada.
Memória 633: alvo = 0,20·300.000 = 60.000; F_eff = CT − A = 444.417,96 − 222.000 =
222.417,96; `A_max = (300.000 − 15.000 − 60.000 − 222.417,96) / 1` =
**R$ 2.582,04**. ✔
Verificação independente: arrematando por R$ 2.582,04, o resultado líquido é
exatamente R$ 60.000 e a margem é exatamente 20% de V. A matemática está
**correta e internamente consistente**.

## 4. Lance inicial, débitos e meta — respostas diretas

- **Lance R$ 222.000** vem de `Auction.bid_value` (cadastro do leilão), usado como
  `bid`/`aquisicao`. Não é inventado pelo motor.
- **Débitos somados exatamente uma vez?** Sim. Cada custo cadastrado entra uma única
  vez no breakdown; a tabela `debts` está vazia (os débitos de condomínio/IPTU foram
  cadastrados como CUSTOS, não como `debts`); a precedência de comissão impede dupla
  contagem da comissão.
- **Meta de 20%:** aplicada como MARGEM_MINIMA = 0,20 **sobre o valor de venda**
  (margem sobre venda), não sobre o custo.
- **Custos desconhecidos / provisório vs definitivo:** ITBI, registro, comissão,
  corretagem e tributo estão todos informados → `preco_maximo_definitivo = True`.

## 5. Causa raiz da divergência confirmada

**Defeito de classificação (não de total).** `canonical_cost_key()` só reconhecia
rótulos que batessem EXATAMENTE no mapa canônico. Os rótulos livres reais
"Condomínio em débito" e "IPTU em débito" normalizam para `CONDOMINIO_EM_DEBITO` e
`IPTU_EM_DEBITO`, que não existiam no mapa → caíam em **`outros`**
(outros = 200.417,96 = 178.172,41 + 22.245,55).

Impacto: o **custo total estava CORRETO** (os valores eram somados uma vez), mas o
**breakdown apresentava condomínio = 0 e IPTU = 0**, concentrando tudo em "outros" —
prejudicando a leitura, auditoria e qualquer regra futura por categoria.

## 6. Correção aplicada

`backend/app/finance.py`: `canonical_cost_key()` passou a ter três etapas:
1. match EXATO em `CANONICAL_COST_CATEGORY` (comportamento preservado);
2. fallback por **palavra-chave** (substring) via nova tupla `COST_CATEGORY_KEYWORDS`,
   com os conceitos ESPECÍFICOS (comissão, condomínio, IPTU, ITBI, registro, reforma,
   desocupação, jurídico, carregamento) tendo precedência sobre o genérico
   "débito/dívida" — de modo que "Condomínio em débito" seja reconhecido como
   condomínio e não como débito genérico;
3. sem correspondência → `outros`.

Regra de negócio: o roteamento afeta **apenas a classificação/visibilidade** no
breakdown; o valor de cada custo continua somado uma única vez e **o custo total não
muda**.

Resultado pós-correção no cenário 633: condomínio = 178.172,41; IPTU = 22.245,55;
outros = 0; custo total inalterado (444.417,96); custo de saída, resultado,
break-even e preço máximo idênticos.

## 7. Arquivos alterados

- `backend/app/finance.py` — `canonical_cost_key()` + nova tupla
  `COST_CATEGORY_KEYWORDS`.
- `tests/test_finance.py` — 11 testes determinísticos de regressão (roteamento exato,
  fallback por palavra-chave, específico vence débito genérico, desconhecido→outros, e
  o cenário 633 completo: classificação, total sem dupla contagem, custo de saída,
  resultado, break-even, preço máximo e verificação da meta de 20%).
- `docs/AUDITORIA-MOTOR-FINANCEIRO.md` — este relatório.

## 8. Testes executados (resultados reais)

Executados em container a partir do código-fonte do host montado em `/work`:

- `pytest tests/test_finance.py tests/test_finance_assumptions.py
  tests/test_e2e_financeiro.py` → **63 passed**.
- Suíte COMPLETA do backend (`pytest -q`) → **589 passed, 2 skipped** (33,63s).

Integridade do imóvel 633 (banco, inalterada): **9 análises (V1–V9), 9 verdicts,
V10 = 0, 9 financial_analyses**. Nenhuma análise LLM gerada; nenhum dado histórico
alterado.

Observação operacional: o container `backend` em execução NÃO monta o código-fonte
(apenas o volume `backend_storage`); o código fica embutido na imagem. Portanto a
correção só passa a valer na instância em execução após rebuild da imagem do backend.

## 9. Pendências que dependem de decisão de negócio

1. **Base da meta de margem (sobre venda × sobre custo).** Hoje MARGEM_MINIMA = 0,20
   é margem **sobre a venda** (alvo = 0,20·V). Com débitos de ~R$ 200 mil e venda de
   R$ 300 mil, o teto de lance colapsa para R$ 2.582 — matematicamente correto, porém
   pode não ser a intenção do negócio. Decidir se deve existir também uma meta de
   margem/ROI **sobre o custo** (ou documentar explicitamente a convenção atual).
2. **Débitos cadastrados como custos × tabela `debts`.** Os débitos de condomínio e
   IPTU do imóvel 633 estão na tabela `costs` (a tabela `debts` está vazia). O total
   está correto, mas convém padronizar a origem (custo vs dívida) para relatórios e
   para a classificação canônica permanecer consistente.
