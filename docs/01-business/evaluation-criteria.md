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

A aplicabilidade do checklist por modalidade está **Implementada** (`modality_rules.py`, ruleset `modality-v2`, 5 modalidades,
LICITACAO ainda em aberto); a matriz original que dizia "nada implementado" está desatualizada neste ponto
([MATRIZ-CHECKLIST-MODALIDADE](../02-product/specs/MATRIZ-CHECKLIST-MODALIDADE.md)).

**Classificação por evidências — Implementado (v1.0.11, regra `evidencias-v1`, `checklist_evidence.py`).** Os itens são
respondidos a partir da matrícula (cadeia registral), das condições oficiais da venda (ou do edital) e dos módulos do Radar
(ocupação, processos, localização, comparáveis, premissas), sem IA e com a evidência vinculada. Critérios:

- item jurídico ou documental só é **Comprovado** com trecho do documento; cadastro e cálculo nunca confirmam item jurídico;
- **Sem restrição identificada** só quando o documento certo foi examinado e lido em sequência contínua de atos; não é
  garantia de inexistência e vem com a ação de conferência (certidão de ônus atualizada, CNIB);
- ausência de informação nunca vira resposta negativa nem "não aplicável";
- **Não aplicável** por evidência só quando a condição do item comprovadamente não existe;
- conhecer a regra de responsabilidade por débitos (condições da venda) não informa o valor da dívida: os dois aparecem
  separados;
- "grande reforma" (item 21) é comparada a uma **referência de análise**, não a uma regra jurídica: premissa
  `checklist.reforma_grande_pct`, padrão de 10% do preço de aquisição, ajustável por imóvel (Financeiro > Premissas) ou no
  catálogo de parâmetros. A origem da referência usada aparece na justificativa; o valor da reforma é premissa do usuário
  (confiança baixa sem vistoria).

Cada evidência tem um tipo: fato documental, regra oficial da venda, cálculo, inferência da IA, informação do usuário ou
informação não localizada (registro de que o documento examinado não contém o fato).

## 2. Riscos

**Implementado** (`risk_engine.py`): item de checklist com RISCO_IDENTIFICADO gera risco de severidade ALTA; ATENCAO gera MEDIA.
Só gera risco **com evidência**. Severidade CRITICA existe como categoria (usada por hard stop e veredito).

## 3. Veredito

**Implementado** (`verdict_engine.py`), em ordem de precedência:

1. risco CRITICA ativo: DESFAVORAVEL;
2. financeiro inviável: DESFAVORAVEL;
3. risco ativo: ATENCAO;
4. pendências ou ausência de evidência: INCONCLUSIVO;
5. caso contrário: FAVORAVEL.

Os fatores do veredito (`decisao.fatores`) separam, sem perder pendência, impedimentos jurídicos ou documentais,
informações essenciais desconhecidas, premissas financeiras não configuradas, riscos que reduzem a confiança e itens não
aplicáveis à modalidade, cada um com justificativa e ação. Não alteram a decisão.

O veredito deve apresentar o que se sabe, o que não se sabe, riscos, evidências, impacto financeiro, pendências e mudanças desde a
análise anterior (princípio do produto).

## 4. Análise financeira

**Implementado. Composição única (consistência financeira v2):** o cálculo do veredito (`services.build_finance` →
`viability.verdict_finance`) e a inteligência de mercado (`viability.market_intelligence`) usam as mesmas entradas, a mesma
composição de custos e as mesmas fórmulas. Para as mesmas premissas, custo total, resultado, ROI, break-even e preço máximo
são iguais nos dois.

- **Composição** (`viability.acquisition_costs`): aquisição, comissão (precedência AUCTION_FIXO, AUCTION_PERCENTUAL,
  CUSTO_CADASTRADO), ITBI, escritura e registro, certidões, condomínio e tributos em atraso (com o teto de responsabilidade da
  venda direta Caixa), reforma, regularização, desocupação, custos e dívidas cadastrados fora dessas linhas, IPTU e condomínio
  durante a posse (mensal × prazo).
- **ITBI:** custo cadastrado; senão alíquota informada × maior entre aquisição e base mínima (ESTIMADO, com origem). Sem
  alíquota ou sem preço de aquisição: PENDENTE, fora da soma.
- **Natureza de cada valor:** confirmado, premissa do usuário, estimado, pendente com reserva (reserva do sistema ou manual,
  com origem), pendente fora da soma (nunca zero) e não aplicável.
- **Saída:** corretagem sobre a venda; IR = alíquota × (venda − corretagem − custo dedutível), em que só lance, comissão, ITBI,
  registro e reforma são dedutíveis (dívidas, desocupação, certidões, regularização e condomínio/IPTU da posse não: premissa
  conservadora). Base VENDA quando o usuário a informa. Corretagem e IR não informados usam o padrão declarado (6% e 15%),
  sinalizado.
- **Provisório** quando há custo pendente fora da soma, reserva do sistema, valor de venda estimado (não confirmado) ou
  corretagem/IR/prazo padrão: o veredito não declara o financeiro VIÁVEL.
- **Preço máximo:** maior aquisição que atende a meta do usuário (LUCRO_MINIMO, MARGEM_MINIMA ou ROI_MINIMO), pela mesma função
  do cenário (ITBI, comissão e reserva de registro acompanham o preço). Sem meta do usuário, o veredito não calcula preço máximo;
  a inteligência de mercado mostra uma referência pelo ROI padrão, identificada como tal.
- **Cenários do usuário** (`cenarios` nas premissas): mesma composição, IR e preço máximo; os valores informados no cenário
  (venda, reforma, desocupação, carregamento, prazo) substituem só os itens correspondentes.
- Deságio = 100 × (1 − lance / avaliação); yield sobre o custo total.
- O motor `finance.calculate_financial` continua existindo e fornece os campos legados (desconto, aluguel, detalhe da comissão);
  os indicadores acima vêm da composição única.

**Planejado** (lacunas registradas em `MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS`): TIR, VPL e fluxo
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
| Classificação por evidências (matrícula, condições da venda, módulos do Radar) | Implementado (v1.0.11) |
| Selic de referência para o item 22 | Planejado (não cadastrada; o item mostra o ROI anualizado e fica pendente) |
| Riscos e veredito | Implementado |
| Motor financeiro (composição única do veredito e da inteligência de mercado) | Implementado |
| Cenários conservador/base/otimista e cenários do usuário | Implementado |
| TIR/VPL, sensibilidade | Planejado |
| Parametrização fiscal por jurisdição | Planejado |
| Workflow F0-F13 e hard stops | Implementado |
| Teses fiscais e de ocupação (§9) | Em discussão |
