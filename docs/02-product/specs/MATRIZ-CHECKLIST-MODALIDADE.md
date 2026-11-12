# MATRIZ CHECKLIST × MODALIDADE

> **Situação (reestruturação documental): ATUALIZAR.** O texto abaixo é um diagnóstico da "Fase Zero" e afirma "nada implementado".
> Hoje a aplicabilidade do checklist por modalidade **está implementada** em `backend/app/modality_rules.py` (ruleset
> `modality-v1`, 5 modalidades, LICITACAO em aberto) e exposta em `GET /api/oportunidades/{id}/checklist-aplicavel`.
> Leia o documento como histórico de planejamento; o estado real está em [modules/opportunities-workflow.md](../modules/opportunities-workflow.md).

> **Fase Zero / diagnóstico.** Planejamento. Nada implementado. Mapeia os **27 `canonical_key`
> existentes** (preservados, imutáveis) contra as modalidades-alvo e propõe a estrutura de um
> **checklist dinâmico** (épico D) sem renomear/remover nenhuma chave canônica.

## Regra de ouro

- **Preservar os 27 `canonical_key`.** Não renomear nem remover sem migração compatível.
  A expansão é **aditiva**: novos itens, novos estados e novos campos entram sem tocar os 27.
- A variação por modalidade/UF/fase/tipo/ocupação/finalidade é **parametrização** do
  checklist, não substituição.

## Modalidades-alvo (F1)

| Código | Descrição | Trilha |
|---|---|---|
| `EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA` | Execução extrajudicial da Lei 9.514/97 (foco do produto) | Principal |
| `EXTRAJUDICIAL_OUTRA_GARANTIA` | Outras garantias extrajudiciais | Principal |
| `JUDICIAL` | Arrematação judicial (CPC) | Separada |
| `VENDA_DIRETA` | Venda direta (sem leilão) | Principal |
| `INDEFINIDO` | Modalidade ainda não evidenciada | Triagem |

## Estados de checklist

| Hoje (7, implementado) | Alvo (10, prompt §6) | Observação de migração |
|---|---|---|
| `PENDENTE` | `NAO_INICIADO`, `PENDENTE_DOCUMENTO` | desdobrar aditivamente |
| `EM_ANALISE` | `EM_VALIDACAO` | mapear |
| `CONFIRMADO` | `CONFIRMADO` | igual |
| `RISCO_IDENTIFICADO` | (permanece como sinal de risco) | manter |
| `ATENCAO` | (permanece) | manter |
| `NAO_IDENTIFICADO` | `NAO_CONFIRMADO` | mapear |
| `NAO_APLICAVEL` | `NAO_APLICAVEL_JUSTIFICADO` | exigir justificativa |
| — | `DIVERGENTE` | **novo** |
| — | `VENCIDO` | **novo** (validade) |
| — | `BLOQUEADO` | **novo** (hard stop / dependência) |
| — | `REVISAR` | **novo** |

> A migração de estados deve ser **aditiva + mapeamento**, nunca renomeação destrutiva. Os
> estados atuais continuam válidos; os novos entram como superset.

## Campos-alvo por item (hoje × alvo)

| Campo | Existe hoje (`master_items()`) | Alvo (prompt §6) |
|---|---|---|
| `canonical_key` | ✅ | manter |
| `question` / `description` | ✅ | manter |
| `category` / `domain` | ✅ | manter |
| `priority` | ✅ (índice) | manter |
| `required` | ✅ (índice ≤ 15) | evoluir p/ criticidade |
| `applicable` / `active` / `version` | ✅ | manter |
| `expected_evidence` | ✅ (vazio) | **preencher (evidência mínima)** |
| `related_rules` | ✅ (vazio) | **vincular à Central Jurídica** |
| `risk_categories` | ✅ | manter |
| **criticidade / hard stop** | ❌ | **novo** |
| **aplicabilidade por modalidade/UF/fase/tipo** | ❌ | **novo** |
| **responsável / prazo / validade** | ❌ | **novo** |
| **critérios aprovação/reprovação/inconclusivo** | ❌ | **novo** |
| **dependências entre itens** | ❌ | **novo** |

## Os 27 `canonical_key` × aplicabilidade por modalidade (proposta)

> Legenda: ✅ aplicável · ⚠️ condicional (depende de fato/evidência) · ➖ geralmente não
> aplicável · **(C)** candidato a **hard stop**. **Proposta de curadoria — exige validação
> jurídica antes de virar regra (épico D/E).**

| # | canonical_key | Categoria | EXTRAJ. A.F. | EXTRAJ. OUTRA | JUDICIAL | VENDA DIRETA |
|---|---|---|---|---|---|---|
| 1 | INTIMACAO_PESSOAL | JURIDICO | ✅ (C) | ⚠️ | ➖ | ➖ |
| 2 | INTIMACAO_EDITAL | JURIDICO | ✅ | ⚠️ | ➖ | ➖ |
| 3 | NOTIFICACAO_DOIS_LEILOES | JURIDICO | ✅ (C) | ⚠️ | ➖ | ➖ |
| 4 | QUITACAO_80 | JURIDICO | ✅ | ⚠️ | ➖ | ➖ |
| 5 | GARANTIA_DIVIDA_TERCEIRO | JURIDICO | ⚠️ | ⚠️ | ➖ | ➖ |
| 6 | LANCE_MENOR_50_AVALIACAO | JURIDICO | ⚠️ | ⚠️ | ✅ (preço vil) | ➖ |
| 7 | ACAO_QUESTIONAMENTO | JURIDICO | ✅ | ✅ | ✅ | ⚠️ |
| 8 | LEILOES_NEGATIVOS_AVERBADOS | DOCUMENTAL | ✅ | ⚠️ | ⚠️ | ➖ |
| 9 | CONSOLIDACAO_REGISTRADA | DOCUMENTAL | ✅ (C) | ⚠️ | ➖ | ➖ |
| 10 | PENHORA_INDISPONIBILIDADE | JURIDICO | ✅ (C) | ✅ (C) | ✅ (C) | ✅ (C) |
| 11 | TERCEIRO_OCUPANTE | DESOCUPACAO | ✅ | ✅ | ✅ | ✅ |
| 12 | LOCACAO_REGISTRADA | DESOCUPACAO | ✅ | ✅ | ✅ | ✅ |
| 13 | EDITAL_LIDO | DOCUMENTAL | ✅ (C) | ✅ (C) | ✅ (C) | ➖ |
| 14 | EVICCAO | JURIDICO | ✅ | ✅ | ✅ | ✅ |
| 15 | RESPONSABILIDADE_DEBITOS | FINANCEIRO | ✅ | ✅ | ✅ | ✅ |
| 16 | VAGA_MATRICULA | DOCUMENTAL | ✅ | ✅ | ✅ | ✅ |
| 17 | ILIQUIDEZ | MERCADO | ✅ | ✅ | ✅ | ✅ |
| 18 | CONDOMINIO_ALTO | FINANCEIRO | ✅ | ✅ | ✅ | ✅ |
| 19 | COMPARAVEIS_SUFFICIENTES | MERCADO | ✅ | ✅ | ✅ | ✅ |
| 20 | REGIAO_SERVICOS | MERCADO | ✅ | ✅ | ✅ | ✅ |
| 21 | REFORMA_GRANDE | FINANCEIRO | ✅ | ✅ | ✅ | ✅ |
| 22 | RETORNO_SELIC | FINANCEIRO | ✅ | ✅ | ✅ | ✅ |
| 23 | PRAZO_DOIS_ANOS | FINANCEIRO | ✅ | ✅ | ✅ | ✅ |
| 24 | DISTANCIA_USUARIO | OPERACIONAL | ✅ | ✅ | ✅ | ✅ |
| 25 | REFORMA_LIQUIDEZ | MERCADO | ✅ | ✅ | ✅ | ✅ |
| 26 | CONDOMINIO_PORTARIA | MERCADO | ✅ | ✅ | ✅ | ✅ |
| 27 | ETICA_OCUPACAO | DESOCUPACAO | ⚠️ | ⚠️ | ⚠️ | ⚠️ |

**Leitura:** os itens 1–9 são fortemente específicos da **alienação fiduciária
extrajudicial** (intimação, dois leilões, consolidação) e **não** se aplicam à venda direta;
o item 6 (preço vil 50%) é típico do **judicial** e **não** deve ser piso universal no
extrajudicial (ver `REVISAO-ANOTACOES-LEILAO.md`); itens 17–26 (mercado/financeiro/
operacional) são praticamente universais. **Esta matriz é proposta de curadoria e precisa de
validação jurídica antes de virar regra executável.**

## Itens candidatos a expansão (novos `canonical_key`, aditivos)

Lacunas observadas vs workflow-alvo (a detalhar no épico D, sem alterar os 27):
- **Fiscal/urbanismo (F4):** dívida ativa, sub-rogação de tributos, zoneamento, habite-se,
  área construída divergente, contaminação/desapropriação.
- **Localização/vistoria (F5):** riscos ambientais, vistoria interna realizada, fotos datadas.
- **Registral (F3/F10):** cadeia registral íntegra, correspondência edital×matrícula,
  prenotação/baixa de ônus pós-registro.
- **Posse (F6):** classificação do ocupante evidenciada, locação com cláusula de vigência
  averbada, taxa de ocupação validada (art. 37-A).
- **Financeiro (F7):** custo de capital, TIR mínima, contingência reservada.
- **Decisão (F8):** hard stops explícitos por dimensão.

## Histórico "136 + 27 → 45 regras"

Permanece como **pendência de curadoria** (ver `docs/TODO-CENTRAL-JURIDICA.md`): a base
**implementada** é o Checklist Mestre com 27 `canonical_key`. O conjunto histórico de 136/163
itens brutos e 45 regras canônicas descrito na documentação de origem **não está estruturado
no código** e **não deve ser fabricado** — deve ser recuperado do material-fonte e cadastrado
com rastreabilidade.
