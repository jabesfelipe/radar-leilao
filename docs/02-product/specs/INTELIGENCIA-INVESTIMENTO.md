# SPEC — Inteligência do investimento (Resumo, riscos consolidados, IPTU, condomínio, mercado, matrícula)

Status: implementado nas branches `feat/inteligencia-investimento` (PR #10) e `feat/inteligencia-completa` (não publicado).
Migration `0027_pesquisa_externa` só para a pesquisa externa.

## 1. Objetivo

Responder ao investidor, numa tela, se deve arrematar, até quanto e o que falta saber, sem esconder risco nem dado ausente,
e com a origem de cada número.

## 2. Diagnóstico (antes desta entrega)

| Problema | Componente | O que existia | O que faltava | Causa | Solução |
|---|---|---|---|---|---|
| Riscos com códigos técnicos e repetidos | `risk_engine.py`, `services.recalculate_risks`, `RiskSection.tsx` | Um `Risk` por versão, título `Checklist: CHAVE`, impacto genérico, tela com origem, versão e `#id` | Linguagem simples, consolidação, o que fazer | Tela lia os registros crus de todas as versões | `risk_presenter.py` + `GET /riscos-consolidados` + nova `RiskSection` |
| Recomendação ATENÇÃO sem dizer o que falta | `verdict_engine.py` | Precedência risco > pendência; texto conta riscos | Pendências essenciais junto do risco; aviso de margem | Regra devolve o primeiro motivo | `investment_summary.recommend` (camada de apresentação; motor intacto) |
| Valor de venda = avaliação × 85% | `viability._inputs` | Estimativa preliminar (decisão 2.2) | Valor de mercado real | Fallback sem comparáveis | Fallback removido: valor desconhecido, AMOSTRA INSUFICIENTE |
| IPTU só com orientação | `IptuGuidanceCard.tsx`, `debt_query_service` | Portal, passos, endpoint `/debitos/consultar` | Status claro e formulário do resultado | Frontend não usava o endpoint | `iptu_status` + `GET /iptu/situacao` + formulário no card |
| Condomínio de 1 anúncio virava custo | `viability.acquisition_costs` | Mediana de qualquer quantidade | Mínimo de referências, faixa, confiança | Sem limiar | Mínimo de 3; `condo_analysis` com média, mediana, faixa |
| Datas da matrícula sem tipo | `registry_timeline.py` | Primeira data do ato | Protocolo × documento × registro; certidão | Leitura só da primeira data | `_typed_dates`, `_protocol`, `certificate_issue` |
| Busca automática de mercado/condomínio | — | Comparáveis manuais | Provedor de pesquisa | Sem API autorizada; scraping viola termos | Status "NÃO CONFIGURADO" explícito |

## 3. Rotas (somente leitura)

- `GET /api/imoveis/{id}/resumo-investimento`: recomendação, números rastreáveis, principal risco, pendências, próximas ações,
  IPTU, condomínio, mercado, Financeiro por natureza e riscos consolidados.
- `GET /api/imoveis/{id}/riscos-consolidados`: riscos do imóvel em linguagem simples.
- `GET /api/imoveis/{id}/iptu/situacao`: situação do IPTU.

O registro do resultado do IPTU usa a rota existente `POST /api/imoveis/{id}/debitos/consultar` (itens ou `sem_ocorrencia`) e,
para o IPTU anual, `PUT /api/imoveis/{id}/financeiro/premissas` (`iptu_anual`, `iptu_anual_origem`).

## 4. Regras

### 4.1 Tipo de dado (rastreabilidade)

FATO (documento, edital, fonte oficial), DADO_MANUAL (informado pelo usuário), ESTIMATIVA (comparáveis, reservas, premissas),
INFERENCIA (conclusão do sistema), DESCONHECIDO (não levantado; nunca vira zero).

### 4.2 Recomendação

1. Risco ativo de gravidade CRÍTICA → NÃO ARREMATAR.
2. Veredito DESFAVORÁVEL ou lance acima do preço máximo definitivo → DESFAVORÁVEL.
3. Risco confirmado ou possível, dado essencial faltando, veredito ATENÇÃO/INCONCLUSIVO ou sem análise → ATENÇÃO — INVESTIGAR.
4. Caso contrário → FAVORÁVEL.

Com resultado positivo e recomendação diferente de FAVORÁVEL, aparece o aviso "a margem estimada é positiva, mas não basta".
Dados essenciais: valor de venda, IPTU consultado, taxa de condomínio, dívida de condomínio, custos críticos pendentes e
pendências essenciais do checklist. O estado do motor do veredito (`FAVORAVEL/ATENCAO/DESFAVORAVEL/INCONCLUSIVO`) não mudou.

### 4.3 Riscos consolidados

- Chave de consolidação: chave canônica do checklist lida do `origin`/`description` (`CHECKLIST_<CHAVE>_<ESTADO>`).
- Estado mais recente; risco ausente na versão do veredito mais recente = RESOLVIDO.
- RISCO_IDENTIFICADO → CONFIRMADO; ATENCAO → POSSÍVEL; ocupação registrada como confirmada → CONFIRMADO.
- Item essencial do checklist pendente → PENDENTE DE CONFIRMAÇÃO; item sem restrição → NÃO IDENTIFICADO.
- Categorias: Jurídico, Ocupação e desocupação, Financeiro, Débitos, Documentação, Mercado, Reforma, Liquidez, Operacional.
- Estimativa: linha de custo do Financeiro ligada ao risco (ex.: desocupação); sem linha, "sem estimativa".
- Histórico das versões fica em `rastreabilidade.historico` (não exibido).

### 4.4 IPTU

| Situação | Quando |
|---|---|
| CONSULTADO | Consulta concluída, sem ocorrência ou débito de IPTU registrado |
| CONSULTA ASSISTIDA | Consulta iniciada aguardando o resultado (`REQUER_INTERVENCAO_MANUAL`) |
| PENDENTE DE CONSULTA | Sem consulta, com município e inscrição |
| NÃO ENCONTRADO | Portal não achou o imóvel |
| FALHA NA CONSULTA | Erro ou portal indisponível |
| NECESSITA INFORMAÇÃO | Sem município na cobertura ou sem inscrição imobiliária |

Os 4 portais levantados exigem CPF/CNPJ, login ou têm bloqueio contra robôs: não há automação. A tela mostra o portal, os dados
exigidos, o motivo e o formulário do resultado.

### 4.5 Condomínio

- Taxa mensal exibida = a mesma usada no Financeiro (fonte única). Origem: premissa do usuário > mediana de 3+ comparáveis usados >
  parâmetro do catálogo > desconhecido.
- Anúncios do mesmo endereço aparecem à parte (ANÚNCIO), sem mudar o cálculo.
- Dívida acumulada vem da linha `condominio_atraso` e nunca é somada à taxa.
- Taxa extra: sem fonte automática, sempre "desconhecido".

### 4.6 Mercado

- Qualidade da amostra: INSUFICIENTE (< 3), BAIXA (3 até < mínimo do método, padrão 7), MÉDIA (mínimo com dispersão alta),
  ALTA (mínimo com dispersão controlada).
- Sem valor do usuário e sem amostra: valor de venda desconhecido. Avaliação × percentual não é usada.
- Yield bruto = aluguel estimado × 12 ÷ valor de mercado (e ÷ preço de compra).

### 4.7 Matrícula

- Datas do ato com tipo pela palavra mais próxima antes da data (protocolo, documento apresentado, registro/averbação); sem palavra,
  "citada". Nenhuma data deduzida.
- Número do protocolo quando escrito no ato.
- Emissão da certidão só com "Data/hora", "emitida em", "expedida em" ou "certifico e dou fé" seguido de data.

## 5. Evolução completa (branch `feat/inteligencia-completa`)

- **Pesquisa externa** (SPEC `PESQUISA-EXTERNA.md`): Tavily/Brave por API, cache, retry, alternativo, registro; anúncios viram
  comparáveis rastreáveis; roda na análise quando configurada.
- **Riscos**: categorias Ocupação e Desocupação separadas; cada risco ganha por que importa, impacto por dimensão (financeiro,
  prazo, operacional, jurídico), confiança, fonte, próxima ação e mitigação; ponto de atenção sem documento é explicado.
- **Checklist P0–P3** (`checklist_priority.py`): P0 bloqueadores (consolidação, edital, débitos, ação judicial, penhora,
  comparáveis), P1 riscos críticos, P2 importantes, P3 complementares; o payload do checklist ganha `prioridade`, `explicacao`,
  `proxima_acao`, `responsavel`; a aba ordena itens em aberto por prioridade; `GET /api/imoveis/{id}/checklist-prioritario`.
- **Documentos** (`document_status.py`): recebidos, analisados, incompletos, obrigatórios (matrícula, edital ou condições da
  venda), recomendados (IPTU, condomínio, laudo/fotos), evidências e páginas citadas, próxima ação; vem em
  `GET /api/imoveis/{id}/documentos` (`situacao_documental`) e `GET /api/imoveis/{id}/documentos/situacao`.
- **Matrícula**: tipos Intimação e Inadimplência; pessoas envolvidas (uma linha por pessoa, papéis, atos, proprietário atual,
  quem perdeu o imóvel na consolidação, construtora); emissão da certidão só em contexto da própria certidão.
- **IPTU**: exercício, vencimento e parcelamento no registro da consulta; lançamentos e portal encontrado por pesquisa no Resumo.
- **Resumo**: cenários Conservador/Provável/Otimista com premissas, margem de segurança, checklist P0/P1, documentos, alertas
  (liquidez baixa, amostra baixa) que impedem FAVORÁVEL, e pesquisa automática.

## 6. Limitações

- Sem provedor de pesquisa de anúncios: comparáveis de venda, aluguel e condomínio continuam cadastrados à mão.
- IPTU depende da consulta do operador nos 4 municípios levantados.
- O tipo da data depende da qualidade do OCR.
- A recomendação é camada de apresentação; o veredito persistido continua com o estado do motor.
