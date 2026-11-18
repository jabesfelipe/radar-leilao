# MATRIZ CHECKLIST × MODALIDADE

> **Situação:** a aplicabilidade do checklist por modalidade **está implementada** em `backend/app/modality_rules.py`
> (ruleset `modality-v2`, 5 modalidades, LICITACAO em aberto), aplicada a cada execução do checklist e exposta em
> `GET /api/oportunidades/{id}/checklist-aplicavel`. A regra **implementada** para a venda direta está na seção abaixo; a
> partir de "Fase Zero / diagnóstico" o texto é o histórico de planejamento (proposta de curadoria).

## Regra implementada para VENDA_DIRETA (modality-v2)

Decidida pela **finalidade** do item, não pelo rito: etapa de leilão que não existe → não aplicável; validade da execução
fiduciária que originou o título do vendedor → condicional (continua PENDENTE e reduz a confiança); situação registral,
condições da venda, ocupação, mercado e financeiro → aplicável. Cada item guarda a justificativa e a regra
`modality-v2:VENDA_DIRETA:<chave>`. As demais modalidades não mudaram; INDEFINIDO mantém tudo aplicável.

| # | canonical_key | Aplicabilidade | Motivo |
|---|---|---|---|
| 1–5 | INTIMACAO_PESSOAL, INTIMACAO_EDITAL, NOTIFICACAO_DOIS_LEILOES, QUITACAO_80, GARANTIA_DIVIDA_TERCEIRO | Condicional | Validade da execução de origem; o ex-devedor ainda pode questioná-la. |
| 6 | LANCE_MENOR_50_AVALIACAO | Não aplicável | Não há segundo leilão nem lance; o preço é comparado ao mercado no financeiro. |
| 7 | ACAO_QUESTIONAMENTO | Aplicável | Ação contra a execução ou o vendedor. |
| 8 | LEILOES_NEGATIVOS_AVERBADOS | Condicional | Situação registral quando o título vem de consolidação. |
| 9 | CONSOLIDACAO_REGISTRADA | Aplicável | Situação registral: comprova que o vendedor é o proprietário. Respondido pela cadeia registral da matrícula. |
| 10 | PENHORA_INDISPONIBILIDADE | Aplicável | Ônus atual na matrícula. Desde a v1.0.11, matrícula lida em sequência contínua sem restrição → "sem restrição identificada" (não é garantia de inexistência). |
| 11–12 | TERCEIRO_OCUPANTE, LOCACAO_REGISTRADA | Aplicável | Ocupação. |
| 13 | EDITAL_LIDO | Não aplicável | Sem edital; volta a ser aplicável se um documento do tipo EDITAL for anexado. |
| 14 | EVICCAO | Aplicável | Vem das condições da venda. |
| 15 | RESPONSABILIDADE_DEBITOS | Aplicável | Condições oficiais da venda, mesmo sem edital; com as condições informadas nas premissas fica INCONCLUSIVO até o documento ser anexado. |
| 16–27 | demais itens | Aplicável | Mercado, financeiro, documentação e preferências do investidor. |

A aplicabilidade acima não mudou na v1.0.11. Mudaram a justificativa dos itens 1–5 (cada um diz qual fato precisa ser
comprovado e onde ele costuma estar) e a pergunta exibida do item 15 na venda direta: "Quais são as responsabilidades do
comprador e do vendedor pelos débitos de IPTU e condomínio anteriores à aquisição?". A pergunta do catálogo não muda.

## Classificação por evidências (evidencias-v1, v1.0.11)

Fonte única no backend: `backend/app/checklist_evidence.py`, alimentado pela cadeia registral (`registry_chain.py`), pelas
condições oficiais da venda (`sale_conditions.py`) e pelos módulos de ocupação, processos, localização, mercado e premissas.
Vale para todas as modalidades; a regra de modalidade continua decidindo o que é aplicável.

Regras comuns:

1. Só muda item aplicável ainda PENDENTE ou INCONCLUSIVO. Resposta do usuário ou de agente com citação válida prevalece.
2. Item jurídico ou documental só é CONFIRMADO com trecho do documento. Cadastro, cálculo e premissas respondem itens de
   mercado, ocupação, financeiro e preferência, com a origem declarada e confiança BAIXA quando não há documento.
3. Ausência no texto nunca vira "não". "Sem restrição identificada" (estado NAO_IDENTIFICADO) exige a matrícula lida com ao
   menos dois atos em sequência contínua (sem número de ato faltando); o texto diz que não é garantia de inexistência.
4. NAO_APLICAVEL por evidência só quando a condição do item comprovadamente não existe (ex.: venda direta cuja matrícula lida
   não tem alienação fiduciária nem consolidação: itens 1–5 e 8).
5. Item que segue pendente recebe justificativa própria (o que se sabe, o que falta, onde buscar) e a regra
   `evidencias-v1:<chave>`.

Resultado exibido ao investidor (derivado do estado gravado, também para análises antigas): Comprovado (CONFIRMADO), Risco
identificado (RISCO_IDENTIFICADO ou ATENCAO), Pendente, Inconclusivo (EM_ANALISE), Não aplicável e Sem restrição identificada
(NAO_IDENTIFICADO).

| # | Item | Fonte usada | Resultados possíveis |
|---|---|---|---|
| 1 | Intimação pessoal | Matrícula: atos que citam intimação pessoal, edital ou certidão de não pagamento | Comprovado (pessoal citada); Inconclusivo (só edital citado); Pendente (consolidação sem o meio da intimação) |
| 2 | Intimação por edital | Idem | Comprovado (edital citado); Não aplicável (só a pessoal citada); Pendente |
| 3 | Notificação dos leilões | Matrícula (raramente averbada); comprovante do vendedor | Comprovado (comunicação citada); Pendente |
| 4 | Quitação de 80% | Matrícula traz a dívida, não os pagamentos | Pendente, com o valor da dívida registrado (ex.: R-3) e o documento que falta |
| 5 | Garantia de dívida de terceiro | Registro da alienação fiduciária | Sem restrição identificada (mútuo da própria aquisição); Risco (garantia de terceiro citada); Pendente |
| 7 | Ação questionando a execução | Averbação de ação/citação na matrícula; processos vinculados | Risco (ação averbada); Inconclusivo (processos cadastrados); Pendente (ações sem averbação não aparecem na matrícula) |
| 8 | Leilões negativos averbados | Matrícula | Comprovado (averbação de leilões negativos); Inconclusivo (leilão citado sem resultado, termo de quitação, ou consolidação sem averbação de leilões); Pendente (sem matrícula) |
| 9 | Consolidação registrada | Matrícula | Comprovado (alienação + consolidação); Inconclusivo (só a alienação) |
| 10 | Penhora/indisponibilidade | Matrícula: penhora, indisponibilidade, arresto, sequestro e cancelamentos | Risco (vigente); Inconclusivo (cancelada depois, ou leitura com lacunas); Sem restrição identificada (lida em sequência contínua) |
| 11 | Terceiro ocupante | Cadastro de ocupação; cessão de direitos na matrícula | Risco (ocupado ou cessão registrada); Sem restrição identificada (desocupado); Pendente |
| 12 | Locação registrada | Matrícula | Risco (locação registrada); Sem restrição identificada (lida em sequência contínua); Pendente |
| 14 | Evicção | Condições da venda (CONDICOES_VENDA) ou edital | Comprovado (vendedor responde, com ou sem limite); Risco (exclusão expressa); Inconclusivo (sem cláusula ou redação ambígua); Pendente (sem documento) |
| 15 | Débitos de IPTU e condomínio | Condições da venda ou edital (regra); dívidas cadastradas (valor) | Comprovado (regra de condomínio e de IPTU lidas); Inconclusivo (falta uma regra, limite sem a regra do excedente, ou só premissas); Pendente |
| 16 | Vaga com matrícula própria | Matrícula e cadastro (vagas) | Comprovado ("Sim" ou "Não, vinculada"); Inconclusivo (cadastro tem vaga, matrícula não descreve); Não aplicável (0 vaga e matrícula sem vaga) |
| 17 | Iliquidez | Liquidez da inteligência de mercado | Risco (BAIXA); Sem restrição identificada (MÉDIA/ALTA); Pendente (sem comparáveis) |
| 18 | Condomínio alto | Comparáveis (mediana); condomínio do imóvel não é cadastrado | Pendente, com a mediana dos comparáveis |
| 19 | Comparáveis suficientes | Comparáveis cadastrados | Comprovado (7+ de venda e de aluguel, regra v1.0.4); Pendente com as quantidades |
| 20 | Região | Checklist de localização | Comprovado (sem RUIM, vizinhança avaliada); Risco (algum RUIM); Inconclusivo (vizinhança não avaliada); Pendente (menos de 3 critérios) |
| 21 | Grande reforma | Premissa de reforma × preço de aquisição, comparada à referência de análise `checklist.reforma_grande_pct` (premissa do imóvel > catálogo de parâmetros > padrão de 10%) | Risco (a partir da referência); Sem restrição identificada (abaixo); Pendente. A referência é premissa ajustável, não regra jurídica |
| 22 | Retorno x Selic + 15% | ROI do cenário base | Pendente: a Selic de referência não é cadastrada no Radar; a justificativa mostra o ROI anualizado |
| 23 | Prazo de dois anos | Prazo nas premissas (regra v1.0.4) | Risco (24 meses ou mais, ATENCAO); Sem restrição identificada (menos de 24); Pendente |
| 24, 26 | Distância, portaria | Não há dado no Radar | Pendente, com a ação |
| 25 | Obras para liquidez | Vistoria (não cadastrada) | Pendente, com a liquidez estimada |
| 27 | Ocupação por família | Cadastro de ocupação | Não aplicável (desocupado); Pendente (decisão do investidor) |

As condições da venda são lidas de documentos anexados com o tipo `CONDICOES_VENDA` (aceita "Condições da venda") ou
`EDITAL`. A matrícula e as condições são fontes separadas: nenhuma cláusula comercial é procurada na matrícula. Regras de
débito reconhecidas: "comprador até o limite, vendedor paga o que exceder" e "comprador dentro do limite, acima dele o vendedor
assume integralmente"; o comparador ("até" ou "abaixo de") vem do texto. Limite sem a regra do excedente fica ambíguo.

### Caso de referência (imóvel 7, sintético)

`tests/test_checklist_evidencias.py::test_caso_imovel7_sintetico_resultado_dos_27_itens`, com a matrícula fictícia de mesma
estrutura (R-3 alienação fiduciária, Av-5 consolidação citando a certidão "pós edital"), condições da venda fictícias e o
leilão (avaliação), sem comparáveis, ocupação, localização ou premissas, como o imóvel está hoje em produção:

| Itens | Resultado | Motivo |
|---|---|---|
| 02, 09, 14, 15 | Comprovado | Av-5 cita o edital; R-3 + Av-5; cláusula de evicção; regras de condomínio e IPTU |
| 05, 10, 12 | Sem restrição identificada | R-3 garante o mútuo da própria aquisição; atos 1 a 5 lidos sem penhora nem locação |
| 01, 08, 16 | Inconclusivo | edital indica que a intimação pessoal não se concretizou; consolidação sem averbação de leilões; cadastro tem vaga que a matrícula não descreve |
| 06, 13 | Não aplicável | regra de modalidade |
| 03, 04, 07, 11, 17–27 | Pendente | cada um com a justificativa e a ação próprias |

Sem o documento de condições anexado, 14 e 15 ficam Pendentes pedindo o documento CONDICOES_VENDA (é o caso do imóvel 7 em
produção até a próxima análise com o documento).

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
