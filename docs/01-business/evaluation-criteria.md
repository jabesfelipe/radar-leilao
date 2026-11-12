# Critérios de avaliação

Como o Radar avalia um imóvel. Cada critério é classificado em **Implementado** (existe no código e foi conferido),
**Planejado** (aceito como direção, sem código) ou **Em discussão** (hipótese de anotações, sem decisão nem fonte oficial).
Referências de código são do estado atual de `main`.

## 1. Checklist mestre

**Implementado.** `backend/app/checklist.py` define 27 itens (`canonical_key`), 15 deles obrigatórios (`required`, posição ≤ 15).
Cada item tem categoria, estado e confiança. Estados: PENDENTE, EM_ANALISE, CONFIRMADO, RISCO_IDENTIFICADO, ATENCAO,
NAO_IDENTIFICADO, NAO_APLICAVEL. Confiança: BAIXA, MEDIA, ALTA.

| Categoria | Itens (`canonical_key`) |
|---|---|
| Jurídico | INTIMACAO_PESSOAL, INTIMACAO_EDITAL, NOTIFICACAO_DOIS_LEILOES, QUITACAO_80, GARANTIA_DIVIDA_TERCEIRO, LANCE_MENOR_50_AVALIACAO, ACAO_QUESTIONAMENTO, PENHORA_INDISPONIBILIDADE, EVICCAO |
| Documental | LEILOES_NEGATIVOS_AVERBADOS, CONSOLIDACAO_REGISTRADA, EDITAL_LIDO, VAGA_MATRICULA |
| Desocupação | TERCEIRO_OCUPANTE, LOCACAO_REGISTRADA, ETICA_OCUPACAO |
| Financeiro | RESPONSABILIDADE_DEBITOS, CONDOMINIO_ALTO, REFORMA_GRANDE, RETORNO_SELIC, PRAZO_DOIS_ANOS |
| Mercado | ILIQUIDEZ, COMPARAVEIS_SUFFICIENTES, REGIAO_SERVICOS, REFORMA_LIQUIDEZ, CONDOMINIO_PORTARIA |
| Operacional | DISTANCIA_USUARIO |

Observação: a chave `COMPARAVEIS_SUFFICIENTES` contém um erro de grafia no código (deveria ser "SUFICIENTES"). Como a chave é
canônica e preservada no histórico (27 `canonical_key`), o erro é registrado aqui e **não** foi corrigido.

A aplicabilidade do checklist por modalidade está **Implementada** (`modality_rules.py`, ruleset `modality-v1`, 5 modalidades,
LICITACAO ainda em aberto); a matriz original que dizia "nada implementado" está desatualizada neste ponto
([MATRIZ-CHECKLIST-MODALIDADE](../02-product/specs/MATRIZ-CHECKLIST-MODALIDADE.md)).

## 2. Riscos

**Implementado** (`risk_engine.py`): item de checklist com RISCO_IDENTIFICADO gera risco de severidade ALTA; ATENCAO gera MEDIA.
Só gera risco **com evidência**. Severidade CRITICA existe como categoria (usada por hard stop e veredito).

## 3. Veredito

**Implementado** (`verdict_engine.py`), em ordem de precedência:

1. risco CRITICA ativo: DESFAVORAVEL;
2. risco ativo: ATENCAO;
3. pendências ou ausência de evidência: INCONCLUSIVO;
4. caso contrário: FAVORAVEL.

O veredito deve apresentar o que se sabe, o que não se sabe, riscos, evidências, impacto financeiro, pendências e mudanças desde a
análise anterior (princípio do produto).

## 4. Análise financeira

**Implementado** (`finance.py`):

- custos por categoria fixa (`COST_KEYS`: aquisição, comissão, ITBI, registro, débitos, condomínio, IPTU, custos jurídicos, desocupação, reforma, carregamento, outros), sem dupla contagem;
- ITBI e registro **não são calculados**: são custos informados; se ausentes, ficam DESCONHECIDO e o resultado é **provisório**;
- precedência da comissão do leiloeiro: AUCTION_FIXO, depois AUCTION_PERCENTUAL, depois CUSTO_CADASTRADO;
- deságio = 100 × (1 − lance / avaliação); margem e yield;
- custos de saída: corretagem e tributo, base GANHO ou VENDA (parametrizável);
- resultado líquido, margem líquida, ROI da operação, break-even;
- preço máximo por meta (LUCRO_MINIMO, MARGEM_MINIMA ou ROI_MINIMO), definitivo ou provisório;
- carregamento mensal × prazo;
- cenário BASE.

**Planejado** (lacunas registradas em `MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS`): cenários OTIMISTA e PESSIMISTA no motor; TIR, VPL e fluxo
descontado; grid de sensibilidade; custo de capital; parametrização de tributos e emolumentos por jurisdição, ato, base, vigência e
fonte oficial.

Estimativa condominial (`estimates_service.py`): três cenários, sempre marcada como ESTIMADO.

## 5. Mercado

**Implementado:** comparáveis de venda e aluguel, estatística com amostra mínima de 7 (`mercado.amostra_minima`) e coeficiente de
variação de dispersão alta 0,30 (`mercado.cv_dispersao_alta`). Parâmetros em `parameter_seeds.py`, administráveis na tela de Administração.

## 6. Parâmetros de negócio semeados

`condominio.periodo_presumido_meses = 12`; `margem_seguranca_pct = 0,10`; `fator_otimista = 0,70`; alerta de idade do imóvel em 10 e 15 anos.

## 7. Hard stops e workflow

**Implementado** (`workflow_rules.py`, ruleset `workflow-v1`): 14 fases (F0 a F13), 9 estados de fase, 8 hard stops. Ver
[workflow no módulo](../02-product/modules/opportunities-workflow.md). Hard stops: MODALIDADE_INDEFINIDA (bloqueia F1), RISCO_JURIDICO_CRITICO,
CONSOLIDACAO_NAO_REGISTRADA, INTIMACAO_MORA_AUSENTE, MATRICULA_DIVERGENTE, USUFRUTO_NAO_EXTINTO, ACAO_ANULATORIA_ATIVA e
PRECO_ACIMA_MAXIMO (todos bloqueiam F8, comitê). A passagem F8 para F9 exige decisão APROVADA.

## 8. Central Jurídica

**Implementado** (`legal_catalog.py`): 5 fontes, 11 dispositivos e 8 regras (Lei 9.514 arts. 26, 27 e 37-A; Código Civil arts. 1.228 e 447;
CPC art. 903; Lei 8.245 art. 8º; CTN arts. 130 e 131). Curadoria: [MATRIZ-CURADORIA-JURIDICA](../02-product/specs/MATRIZ-CURADORIA-JURIDICA.md).

## 9. Em discussão (não implementado, sem decisão)

Hipóteses de anotações do proprietário, a validar com fonte oficial antes de qualquer código
([REVISAO-ANOTACOES-LEILAO](../02-product/specs/REVISAO-ANOTACOES-LEILAO.md)):

- IR de ganho de capital, reinvestimento e redutores por tempo;
- FUNREJUS, ISSQN, FUNDEP e selo;
- taxa de ocupação do art. 37-A (incidência, marco, jurisprudência);
- "preço vil" de 50% (critério do leilão judicial);
- tratamento de certidões (negativa não garante imóvel livre);
- negociação e ajuda de mudança para desocupação.

## 10. Resumo de situação

| Critério | Situação |
|---|---|
| Checklist (27 itens) | Implementado |
| Aplicabilidade por modalidade | Implementado (LICITACAO em aberto) |
| Riscos e veredito | Implementado |
| Motor financeiro BASE | Implementado |
| Cenários OTIMISTA/PESSIMISTA, TIR/VPL, sensibilidade | Planejado |
| Parametrização fiscal por jurisdição | Planejado |
| Workflow F0-F13 e hard stops | Implementado |
| Teses fiscais e de ocupação (§9) | Em discussão |
