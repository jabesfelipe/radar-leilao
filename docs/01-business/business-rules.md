# Regras de negócio e glossário

## 1. Classificação das regras (método do Radar)

| Tipo | Natureza | Exemplos |
|---|---|---|
| Determinística | resultado calculável pelo sistema | custo total, deságio, preço por m², yield, ROI, margem, preço máximo, cenários |
| Documental | depende de evidência em documento | averbação, consolidação, cláusula do edital, matrícula da vaga, responsabilidade por débitos |
| Jurídica | interpretação de fatos, documentos e fontes jurídicas; a IA auxilia, com evidência e nível de confiança | regularidade da intimação, usufruto, ações anulatórias |
| De mercado | depende de comparáveis e dados coletados | liquidez, valor de venda e aluguel |
| De risco | transforma uma condição em impacto operacional, financeiro ou jurídico | risco ALTA/MEDIA gerado pelo checklist |

## 2. Regras gerais verificadas no código

1. **Evidência primeiro.** Risco só é gerado com evidência; sem evidência, o resultado é INCONCLUSIVO.
2. **Dado ausente não é zero.** Custo não informado fica DESCONHECIDO e marca o resultado como provisório.
3. **Preço máximo** é definitivo apenas quando não há custos desconhecidos.
4. **Comissão do leiloeiro:** AUCTION_FIXO > AUCTION_PERCENTUAL > CUSTO_CADASTRADO.
5. **Histórico não é sobrescrito:** análises e análises financeiras são versionadas (V1 a V9 no imóvel de referência).
6. **Isolamento por oportunidade:** dados de uma oportunidade não vazam para outra (ver [SPEC-OPPORTUNITY-ISOLATION](../03-architecture/specs/SPEC-OPPORTUNITY-ISOLATION.md)).
7. **Workflow:** F8 para F9 só com decisão de comitê APROVADA; hard stops ativos impedem o avanço da fase indicada; eventos de invalidação reabrem fases.
8. **Estimativa condominial** é sempre ESTIMADO e usa três cenários.
9. **Modalidade indefinida** bloqueia a triagem (F1).
10. **Autotutela proibida** na desocupação: a consultoria de desocupação modela escopo incluído e excluído; minuta de notificação é rascunho para advogado.

## 3. Regras jurídicas catalogadas

As 8 regras da Central Jurídica estão em [legal.md](../02-product/modules/legal.md). Elas são auxílio à análise, **não** aconselhamento jurídico.

## 4. Regras que dependem de decisão externa

Tributos, emolumentos e ocupação onerosa: ver [evaluation-criteria.md §9](evaluation-criteria.md#9-em-discussão-não-implementado-sem-decisão).
Nenhuma alíquota ou tabela foi cadastrada como verdade.

## 5. Glossário

| Termo | Significado |
|---|---|
| Alienação fiduciária | garantia em que o devedor transfere a propriedade resolúvel ao credor (Lei 9.514/97) |
| Consolidação | registro, na matrícula, da propriedade plena em nome do credor após a mora |
| Dossiê vivo | conjunto versionado de tudo o que se sabe do imóvel |
| Oportunidade (Opportunity) | unidade de negócio do workflow: um imóvel em uma tentativa de arrematação |
| Fase (F0 a F13) | etapa do workflow da oportunidade |
| Hard stop | condição que bloqueia o avanço de uma fase |
| Checklist mestre | 27 perguntas canônicas do método |
| Veredito | síntese explicável: FAVORAVEL, ATENCAO, INCONCLUSIVO, DESFAVORAVEL |
| Deságio | desconto do lance sobre a avaliação |
| Break-even | preço em que o resultado líquido é zero |
| Preço máximo | maior lance que atinge a meta de lucro, margem ou ROI |
| RAG | recuperação de trechos relevantes dos documentos para a IA |
| Central Jurídica | catálogo de fontes, dispositivos e regras jurídicas |
| Modalidade | tipo de venda do imóvel (5 modalidades; LICITACAO em aberto) |
| Imóvel 633 | imóvel de referência (COND PARQUE ARVOREDO RESIDENCIAL CLUBE), protegido contra limpeza |
| Gate (portão) | cookie de acesso do proxy nginx que antecede o login |
| GHCR | registro de imagens do GitHub usado no deploy |
