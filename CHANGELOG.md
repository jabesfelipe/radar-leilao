# Changelog

Formato: uma seção por versão publicada (tag `vX.Y.Z` na `main`). Datas no fuso de Brasília.

## Não publicado — inteligência do imóvel (branch `feat/inteligencia-imovel`)

Sem migration e sem tabela nova. Detalhes e valores padrão em `docs/02-product/specs/INTELIGENCIA-IMOVEL.md`.

- **Fonte única de custos (Fase A).** Condomínio e IPTU em atraso vêm de um leitor só (dívida confirmada > informada >
  estimativa condominial > pendente), usado pela composição, veredito, inteligência de mercado, recomendação e item 15. A
  regra de responsabilidade vem primeiro do documento das condições da venda (trecho literal) e depois das premissas.
  Consulta indisponível nunca vira zero. Item 08 usa "Averbação dos leilões negativos: <situação>" das condições como
  informação do vendedor (inconclusivo). Pendências do veredito agrupadas por assunto, sem perder mensagens.
- **Premissas financeiras no Admin (Fase B).** Aba "Premissas financeiras" sobre o catálogo de parâmetros (mesmo histórico),
  com valor por município (ex.: ITBI). Seed com os mesmos padrões do motor; ITBI, IPTU, condomínio mensal, regularização e
  custos mensais sem valor padrão. Valor de venda preliminar = avaliação × 0,85 (configurável), só sem valor informado e sem
  comparáveis, com selo "Estimativa preliminar" e confiança baixa.
- **Linha do tempo da matrícula (Fase C).** `GET /api/imoveis/{id}/matricula/linha-do-tempo`: atos com data, tipo, partes
  com papel declarado, valor, construtora e conclusão de obra, a partir dos trechos armazenados. Idade só pela conclusão de
  obra; senão "Idade não determinável pela matrícula."
- **Possíveis ocupantes (Fase D).** `GET /api/imoveis/{id}/ocupacao/possiveis-ocupantes` com o aviso obrigatório; novos
  status de ocupação (confirmada, por terceiros, não verificado) e verificação (fonte, data, observação, responsável) em
  evidência vinculada. Itens 11 e 27 só usam o registro do usuário.
- **Estimativa condominial pela matrícula (Fase E).** `POST /api/imoveis/{id}/debitos/estimar-condominio/matricula`:
  período aquisição → consolidação com teto, cenários 15/35/70%, multa, juros e correção configuráveis, regra da venda
  aplicada depois; aviso obrigatório.
- **IPTU dos 4 municípios (Fase F).** Levantamento dos portais de Curitiba, São José dos Pinhais, Fazenda Rio Grande e Assis:
  nenhum permite consulta automatizada (CPF/CNPJ do proprietário, login ou verificação de navegador). Consulta segue manual
  assistida, com portal e passo a passo (`GET /api/imoveis/{id}/debitos/orientacao-iptu`); cobertura de IPTU não editada
  passa de AUTOMATIZAVEL a MANUAL.

## v1.0.11 — 2026-11-18

Checklist por evidências (regra `evidencias-v1`). Sem migration; estados gravados e aplicabilidade por modalidade
(`modality-v2`) sem mudança; análises anteriores preservadas e exibidas com o resultado derivado.

- **Matrícula alimenta os itens que dependem dela.** A cadeia registral passa a ler os atos em sequência (R-n/Av-n) e os
  fatos de intimação (pessoal, edital, não pagamento), leilões negativos ou termo de quitação, notificação dos leilões,
  locação, vaga, ação averbada, cessão de direitos, garantia (mútuo da própria aquisição ou de terceiro) e valor da dívida.
  Itens 1–5, 7, 8, 10, 11, 12 e 16 usam esses fatos, com o trecho vinculado. Penhora, indisponibilidade, arresto e
  sequestro: vigente → risco; cancelada depois → inconclusivo; matrícula lida sem lacuna de atos e sem restrição → "sem
  restrição identificada" (NAO_IDENTIFICADO), com o aviso de que não é garantia de inexistência.
- **Condições oficiais da venda.** Novo tipo de documento `CONDICOES_VENDA` (também aceito "Condições da venda"; opção no
  cadastro). Leitura determinística das cláusulas de condomínio, IPTU/tributos, evicção, FGTS e pagamento. Itens 14 e 15
  respondidos com o trecho; a regra de limite é a do texto (excedente ou integral acima do limite, "até" ou "abaixo de"); o
  valor dos débitos aparece separado da regra. Sem o documento, os itens pedem o documento certo (na venda direta não há
  edital).
- **Módulos do Radar no checklist.** Ocupação (11, 27), processos vinculados (7), checklist de localização (20), liquidez da
  inteligência de mercado (17), premissa de reforma (21) comparada à referência de análise `checklist.reforma_grande_pct`
  (padrão 10% da aquisição; ajustável por imóvel no formulário de premissas ou no catálogo; não é regra jurídica), mediana do condomínio dos
  comparáveis (18), ROI anualizado do cenário base (22) e quantidade de comparáveis (19).
- **Justificativa própria em cada item.** Itens 1–5 dizem qual fato provar e onde; itens pendentes dizem o que já se sabe,
  o que falta e a fonte necessária.
- **Rastreabilidade.** Evidência "informação não localizada" (`origin` NAO_LOCALIZADA) registra o documento examinado e os
  atos lidos. Tipos exibidos: fato documental, regra oficial da venda, cálculo, inferência da IA, informação do usuário,
  informação não localizada. Novo endpoint `GET /api/imoveis/{id}/checklist/{resultado_id}/evidencias`.
- **Tela do checklist.** Resumo por resultado (Comprovado, Risco identificado, Pendente, Inconclusivo, Não aplicável, Sem
  restrição identificada), conclusão, fundamentação, o que fazer, fonte necessária e "Ver evidências" (tipo, documento,
  página, trecho original, confiança, responsável, data). Na venda direta, a pergunta do item 15 passa a ser "Quais são as
  responsabilidades do comprador e do vendedor pelos débitos de IPTU e condomínio anteriores à aquisição?".
- Testes: `tests/test_checklist_evidencias.py` (documentos sintéticos; caso de referência do imóvel 7 com os 27 itens). O
  teste da v1.0.10 que esperava o item 10 pendente com a matrícula lida inteira foi atualizado para a nova regra.

## v1.0.10 — 2026-11-17

Integração da análise de venda direta e consistência financeira. Sem migration (só campos JSON); rollback de imagem
para a v1.0.9 é compatível com o schema.

- **Checklist por finalidade do item (`modality-v2`).** Em VENDA_DIRETA só são não aplicáveis o lance abaixo de 50% e a
  leitura do edital (que volta a ser aplicável se um edital for anexado). Validade da execução de origem (itens 1–5) e
  leilões negativos averbados ficam condicionais e pendentes; consolidação, penhora, evicção e responsabilidade por
  débitos ficam aplicáveis. Cada resultado guarda justificativa e regra. Demais modalidades sem mudança.
- **Itens pela cadeia registral (sem IA).** Consolidação registrada: alienação + consolidação com trecho → CONFIRMADO, só a
  alienação → INCONCLUSIVO. Penhora/indisponibilidade encontrada → RISCO_IDENTIFICADO (a ausência não responde o item).
  Responsabilidade por débitos: INCONCLUSIVO com as condições da venda das premissas. A reanálise incremental segue o mesmo
  fluxo. Efeito no caso 01 de testes: a penhora da matrícula vira risco ALTA e o lance de R$ 120 mil vai a ATENÇÃO.
- **Fatores do veredito.** `decisao.fatores` separa impedimentos, informações essenciais desconhecidas, premissas não
  configuradas, riscos que reduzem a confiança e não aplicáveis, com justificativa e ação. A decisão não muda.
- **Premissas.** Sugestões da inteligência de mercado (valor de venda, corretagem, IR, prazo, carregamento) aplicadas só no
  clique; a meta nunca é sugerida. Salvar o formulário preserva as premissas da v1.0.8 (ITBI, condições Caixa, reservas); a
  origem das condições Caixa deixa de ser descartada. `tributo_pct` com base GANHO é a premissa de IR do motor de viabilidade.
- **Consistência financeira.** O veredito usa a mesma composição de custos, o mesmo IR e o mesmo preço máximo do cenário BASE
  da inteligência de mercado (`viability.verdict_finance`). ITBI pela alíquota entra no custo; corretagem e IR não
  informados usam o padrão declarado, sinalizado e provisório (antes: "assumido 0"); custo sem valor fica pendente, fora da
  soma; certidões, regularização e IPTU/condomínio da posse passam a compor o custo. A corretagem reduz a base do IR e só
  lance, comissão, ITBI, registro e reforma são dedutíveis. Tela: tabela "Composição dos custos" com a natureza de cada valor.
- **Meta única.** A inteligência de mercado calcula o preço máximo pela meta do usuário (ROI, margem ou lucro mínimo), igual ao
  do veredito; sem meta, a referência pelo ROI padrão é identificada como "meta do investidor não configurada".
- **Cenários do usuário** calculados com a mesma composição; os valores do cenário substituem só os itens informados.
- **Caso 01 (gabarito).** Preço máximo de referência R$ 136.266 → R$ 130.804 (provisório), resultado no lance mínimo
  −R$ 26.550 → −R$ 30.457,50, custo total R$ 341.450 → R$ 342.050. A referência anterior fica no gabarito
  (`referencia_regra_anterior`) e continua testada no motor legado. `e2e/valor-negocio` passa a conferir também o status
  provisório e os custos pendentes esperados.
- Imóvel 7 (dados locais de teste): preço máximo BASE com meta ROI 20% = R$ 144.816,84, igual ao validado na v1.0.8; antes
  o veredito mostrava R$ 155.351,64 por não somar ITBI, registro, certidões e reforma.

## v1.0.9 — 2026-11-16

Correção de segurança dos dados de teste e da documentação. Sem migration, sem mudança de regra de negócio.

- **Anonimização dos fixtures de matrícula.** `tests/test_v107_imovel7_regressao.py` usa uma matrícula inteiramente
  fictícia (número, endereço, condomínio, construtora, comprador, banco, protocolos, datas, valores e áreas), com os
  mesmos defeitos de OCR que motivaram a regressão. Novo teste sintético cobre os dois tratamentos da Caixa pelo leitor
  registral (normalização do nome e credor reconhecido sem "em favor da").
- **Imóvel do teste de venda direta (v1.0.7/v1.0.8).** Nome do condomínio e endereço retirados de fixtures, testes,
  docstrings e CHANGELOG; os comparáveis (anúncios públicos de outros imóveis) ficam com fonte e data da coleta.
- **Imóvel de referência 633.** Nome, endereço, matrícula, inscrição imobiliária, código do imóvel, edital, item,
  leiloeiro, áreas, nomes de arquivo e hashes dos PDFs substituídos por dados fictícios coerentes em testes
  (backend e frontend) e documentos.
- **`scripts/db/cleanup_test_properties.sql`.** A trava continua exigindo o id 633 com o título exato, agora o
  fictício `COND RESIDENCIAL EXEMPLO GAMA`; bancos anteriores abortam (comportamento seguro) até a renomeação manual
  descrita no script. Novo `tests/test_cleanup_test_properties.py` roda o script real num schema isolado: preserva só o
  633 e seus dados e aborta sem apagar nada quando o 633 não existe ou o título não confere.
- **Infraestrutura.** IP público da VPS retirado do CHANGELOG.
- Versões e commits anteriores continuam com os dados antigos no histórico do Git (não reescrito).

## v1.0.8 — 2026-11-16

Inteligência de mercado e viabilidade financeira. Migration `0026_comparaveis_rastreaveis` (colunas opcionais).

- **Comparáveis rastreáveis**: natureza do valor (`ANUNCIADO` ou `TRANSACIONADO`), data da consulta, bairro,
  endereço, tipo, quartos, vagas, condomínio, IPTU, base da área, distância medida, observações e exclusão com motivo.
- **Estimativa de mercado** (`market.estimate`): similaridade com o imóvel, duplicatas, discrepantes (Tukey), R$/m²
  anunciado e provável negociado (desconto de negociação configurável), média, mediana, faixa P25–P75 e confiança.
  Menos de 3 comparáveis: só faixa indicativa. Só anúncios: confiança no máximo MÉDIA.
- **Viabilidade** (`backend/app/viability.py`, `GET /api/imoveis/{id}/inteligencia-mercado`): custos com status e
  origem (ITBI, registro, certidões, condomínio e tributos em atraso com a regra da venda direta Caixa, reforma,
  regularização, desocupação, manutenção na posse, corretagem e IR na revenda), cenários conservador/base/otimista,
  preço máximo pelo ROI mínimo configurado, rentabilidade do aluguel sem presumir ocupação de 100%, liquidez e
  conclusão consolidada (FAVORÁVEL só com documentação, risco, mercado, custos, rentabilidade e liquidez completos).
- **Tela**: painel de inteligência de mercado na seção Mercado; formulário de comparável com os novos campos.
- Leitura determinística, sem IA (custo zero). O veredito da análise não muda nesta versão.

### Correções da revisão de regras de negócio (antes da publicação)

- **Cálculo financeiro**: composição de cada cenário item a item, arredondada ao centavo antes de somar (soma dos
  itens = investimento; venda − corretagem − IR − investimento = resultado). Custos e dívidas cadastrados fora das
  linhas padrão deixaram de ser omitidos; comissão cadastrada também como custo não é somada duas vezes.
- **IR sobre ganho de capital**: base = venda líquida da corretagem − custo de aquisição dedutível (aquisição,
  comissão, ITBI, escritura/registro e reforma, IN SRF 84/2001), alíquota de 15%, sem isenções nem fator de redução.
  Condomínio, IPTU, dívidas, certidões, desocupação e regularização não reduzem a base. A memória (itens dedutíveis,
  não dedutíveis, base e alíquota) aparece em todos os cenários, inclusive no conservador. Antes: base = venda − investimento.
- **Margem de segurança**: 1 − venda de equilíbrio ÷ venda estimada, com o mesmo IR do cenário.
- **Regras da venda direta Caixa**, separadas por tipo de dívida: condomínio acima do limite → comprador paga até o
  limite e a Caixa assume o excedente; IPTU/tributos acima do limite → a Caixa assume integralmente; abaixo do limite
  → comprador paga tudo. Dívida de IPTU exatamente igual ao limite → integralmente do comprador (premissa
  conservadora declarada; a regra não esclarece a igualdade). Cada linha mostra dívida total, limite,
  responsabilidade do comprador e valor assumido pela Caixa. Dívida desconhecida: o conservador usa o teto.
- **Pendência nunca vale zero**: cada custo PENDENTE declara o tratamento por cenário (reserva, teto ou fora da
  soma). Registro (2%) e certidões entram em todos os cenários; reforma usa R$ 100/m² no base/otimista e R$ 250/m²
  no conservador. Item fora da soma marca o cenário como incompleto, e a tela mostra o resultado se ele chegar ao
  teto/reserva conhecido.
- **Reservas manuais de regularização e IPTU durante a posse**: `regularizacao_reserva_base/_conservador` e
  `iptu_anual_reserva_base/_conservador`, com origem obrigatória e conservador ≥ base. Não há valor padrão do
  sistema: sem reserva o custo fica PENDENTE e fora da soma. O item segue PENDENTE mesmo com reserva, e o cenário
  continua incompleto se houver outra pendência sem valor.
- **Impacto de cada reserva**: por cenário, efeito de cada reserva/teto no investimento, no resultado, no ROI e no
  preço máximo, calculado com a mesma função do cenário.
- **Pendências no teto (base e otimista)**: memória item a item dos custos fora da soma que têm teto ou reserva
  conhecidos (tipo, dedutibilidade no IR, IR adicional e conferência da conta), lista do que continua sem teto
  conhecido e preço máximo recalculado com esses itens no teto. Se esse preço ficar abaixo da aquisição, a conclusão
  registra um bloqueio.
- **Natureza do valor de cada item no cenário**: confirmado, estimado, reserva, reserva manual, teto Caixa ou fora da soma.
- **Premissas da v1.0.8 pela API**: `PUT /api/imoveis/{id}/financeiro/premissas` passou a aceitar e validar ITBI
  (alíquota e base mínima), registro, certidões, reforma, regularização, IPTU anual, reservas manuais e condições
  Caixa. Antes esses campos eram descartados pelo schema.
- **Preço máximo**: busca binária com a mesma função do cenário, nos três cenários (conservador, base e otimista);
  comprando pelo teto, o ROI é exatamente a meta. Provisório quando há custo sem valor.
- **Comparáveis**: a estimativa lista as limitações da amostra (área total ou sem base declarada, ausência de
  negócio fechado, distância não medida, quartos ausentes, conservação não vistoriada).
- **Aluguel**: rentabilidade sobre o custo de aquisição e preparação (sem o carregamento da revenda), com vacância,
  taxa de administração e condomínio/IPTU dos meses vagos explícitos; antes do IR sobre aluguel; marcado como
  indicativo com menos de 3 comparáveis.
- **Conclusão consolidada**: cenário incompleto impede FAVORÁVEL; aluguel indicativo e amostra só com anúncios
  viram ressalvas (não bloqueiam a tese de revenda).
- **Tela**: legenda Confirmado/Estimado/Pendente, selo de cenário incompleto, preço máximo e ROI no teto por
  cenário, itens fora da soma com o teto conhecido, memória do IR, campos da regra Caixa, impacto das reservas e
  quadro de locação.

## v1.0.7 — 2026-11-15

Correções de qualidade jurídica e documental a partir de um teste real de venda direta (Caixa). Sem migration.

- **Checklist respeita a modalidade do imóvel.** A análise usa a mesma regra de `/api/oportunidades/{id}/checklist-aplicavel`
  (`modality_rules`): em `VENDA_DIRETA`, `EDITAL_LIDO` (e os itens do rito de leilão) nasce `NAO_APLICAVEL`, não vira
  pendência no veredito e não é enviado ao agente. O item continua no catálogo; imóveis de leilão ou sem modalidade
  mantêm todos os itens aplicáveis.
- **Status padronizado** em cada item (`status_padrao`: `RESPONDIDO`, `PENDENTE`, `NAO_APLICAVEL`, `INCONCLUSIVO`) com
  `justificativa` e `evidence_ids` em `GET /api/imoveis/{id}` e `GET /api/imoveis/{id}/checklist`. Tentativa do agente
  com citação insuficiente passa a `INCONCLUSIVO` (estado `EM_ANALISE`), com o motivo; sem citação, segue `PENDENTE`.
- **Cadeia registral determinística** (`backend/app/registry_chain.py`): lê a matrícula em ordem e separa proprietário
  original, intermediários, titular atual, credor fiduciário, alienação fiduciária, consolidação, cancelamentos, ônus e
  áreas total/privativa. Cada conclusão vira evidência com o trecho da matrícula (`agent=cadeia_registral`).
  Consolidação não é tratada como baixa; ausência de ônus no texto lido é `INCONCLUSIVA`, nunca "inexistente".
- **Afirmações dos agentes conferidas**: "não possui ônus", área total apresentada como privativa (ou o inverso) e
  titular atual fora da sequência de atos viram inferência rejeitada, com a regra e a afirmação original. O cadastro
  nunca é alterado; divergência entre cadastro e matrícula é registrada.
- **Extração da matrícula**: `holder` passa a ser o titular atual pela sequência de atos (o valor do modelo fica em
  `campos.holder`); sem ato legível, o campo fica `INCONCLUSIVO`.
- Agentes recebem `area_total_m2`, `area_privativa_m2` e `modalidade` rotulados e a leitura da cadeia registral.

## v1.0.6 — 2026-11-14

Finding com `kind="risco"` (e equivalentes) passa a `interpretacao` em vez de invalidar a resposta do agente checklist.

## v1.0.5 — 2026-11-14

Release operacional: primeira implantação na VPS com a IA (OpenAI) ativada. O código da aplicação é o da v1.0.4.

- VPS de homologação (HTTP) atualizada de v1.0.3 para v1.0.5 pelo `release.yml`, com backup do banco e
  dos documentos e a migration `0025_evidencia_origem_forca`.
- IA no `.env.prod` da VPS: `gpt-4o-mini`, `text-embedding-3-small`, teto mensal de US$ 0,50, teto por análise de
  US$ 0,10, 1.500 tokens de saída, `LLM_REQUIRE_BUDGET=true`, `LLM_REDACT_PII=true`. A chave fica só no `.env.prod`.
- `REQUIRE_HTTPS=false` mantido temporariamente: **só dados sintéticos ou documentos sanitizados** nesse ambiente.
- Rollback: `alembic downgrade 0024_analysis_version_unique` e `scripts/prod/rollback.sh` (volta para a v1.0.3), ou o
  backup gerado pelo deploy em `/opt/radar-backups`.

## v1.0.4 — 2026-11-14

Qualidade da análise por IA, rastreabilidade das evidências e homologação mobile.

### Funcionalidades

- **Rastreabilidade das evidências.** Cada evidência informa a origem (`DOCUMENTO`, `CADASTRO`, `CÁLCULO`, `INFERÊNCIA`) e a força da citação. Citações são validadas contra o texto do documento do próprio imóvel; trecho inexistente ou que não contém o valor afirmado é rebaixado ou descartado (`backend/app/citations.py`, migration `0025_evidencia_origem_forca`).
- **Extração estruturada com referência.** Campos da matrícula e do edital trazem trecho literal e posição no documento; falhas parciais ficam marcadas campo a campo.
- **Confronto documental determinístico** entre matrícula, edital e cadastro (`backend/app/document_comparison.py`), sem custo de IA.
- **Agentes**: regras explícitas de origem, roteiro documental e estados do checklist; pergunta do checklist não é aceita como evidência.
- **Frontend**: selos de origem e força das evidências e exibição do confronto documental no Veredito.

### Correções

- **Orçamento de IA com falha segura**: `LLM_REQUIRE_BUDGET=true` bloqueia chamadas pagas sem teto configurado; custo de resposta truncada contabilizado; modelo sem preço cadastrado é bloqueado.
- **Saída estruturada por function calling** (fim das respostas JSON truncadas).
- **Privacidade**: CPF mascarado também sem formatação; teste do payload realmente enviado ao provider.
- **Privacidade/estabilidade no detalhe do imóvel** (achado na homologação final com IA real): `GET /api/imoveis/{id}` devolvia o objeto ORM em `imovel`, e a serialização incluía todo relacionamento carregado (documentos, chunks com texto bruto sem máscara, caminho do arquivo, evidências sem máscara). Com chunks indexados (embedding) a resposta virava HTTP 500. Agora `imovel` traz só as colunas do imóvel (107 kB → 0,6 kB no caso-01). Teste: `test_property_detail_payload.py`.
- **Isolamento de evidências**: dívida, processo, matrícula, edital, ocupação, débito normalizado, estimativa condominial e modalidade da oportunidade recusam (422) `evidence_id` de outro imóvel ou inexistente. Antes, o imóvel A podia citar evidência do imóvel B. Teste: `test_evidence_ownership.py`.
- **Agente checklist**: `kind='pendente'` (e sinônimos de "não identificado") vira `ausencia` em vez de invalidar todas as findings do agente; valores livres continuam rejeitados.
- **Mobile** (`34f7976`): até 680px a topbar esconde nome/perfil do usuário (a 360px o título virava "C…") e os filtros de Oportunidades passam a ter 44px de altura.
- **Release**: o job de deploy do `release.yml` só roda com a variável de repositório `DEPLOY_ENABLED=true`. Sem ela, a tag valida, testa e publica as imagens no GHCR, mas não altera a VPS.

### Testes adicionados

- Backend: `test_citations`, `test_evidence_traceability`, `test_extraction_references`, `test_document_comparison`, `test_privacy_payload`, `test_budget_pricing`, `test_agent_contract_tolerance`.
- E2E: viewport 1920x1080 e `release.spec.ts` (capturas e checagens de dashboard, menu, imóveis, wizard e seções do detalhe em 360x800, 390x844, 412x915 e 1366x768).

### Resultados desta release

Detalhes em `docs/06-quality/homologacao-v1.0.4/RELEASE-v1.0.4.md`.

- Backend: 1219 passed, 3 skipped (2 DataJud real opt-in, 1 sem `.git` na cópia). Frontend: tsc 0 erros, 182/182, build OK.
- E2E Playwright: 196 passed, 7 skipped (IA paga, desligada por padrão), 0 falhas, em 360×800 a 1920×1080.
- IA real (caso-01, duas execuções): 5/5 agentes, financeiro igual ao gabarito, veredito NÃO ARREMATAR, citações 100% válidas, 0 alucinações detectadas, fatos 11/20 e 15/20, US$ 0,0071 e 0,0077 por execução.
- Isolamento: 19/19 verificações de acesso cruzado OK na API real. Nenhum segredo no histórico, arquivos, logs ou relatórios.

### Configuração necessária

- `.env` (nunca versionado): `OPENAI_API_KEY`, `LLM_BUDGET_USD_MONTH`, `LLM_BUDGET_USD_PER_ANALYSIS`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_REQUIRE_BUDGET=true`, `LLM_REDACT_PII=true`. Ver `.env.example` e `.env.prod.example`.
- Migration nova: `0025_evidencia_origem_forca` (aplicada por `alembic upgrade head`; reversível com `downgrade -1`, verificado no CI).

### Limitações conhecidas

- A VPS continua na v1.0.3, só com HTTP. **Não usar documentos reais** até HTTPS, `REQUIRE_HTTPS=true`, backup e rollback conferidos (`docs/06-quality/homologacao-v1.0.4/PLANO-HTTPS-VPS.md`).
- A IA real foi validada só com o caso sintético `e2e/fixtures/caso-01`; a cobertura de fatos não é total (ver relatório da homologação).
- Validação em aparelho físico ainda depende de teste manual (`docs/HOMOLOGACAO-MOBILE-DESKTOP.md`).

### Rollback

- Código: a v1.0.3 continua disponível pela tag `v1.0.3` (`77ded35`); imagens `backend:v1.0.3`/`frontend:v1.0.3` no GHCR.
- Banco: `alembic downgrade 0024_analysis_version_unique` remove só as colunas novas de origem/força.
- VPS: procedimento em `docs/GITHUB-ACTIONS-DEPLOY.md` §8.

## v1.0.3 — 2026-11-14

Organização dos artefatos e do versionamento dos testes E2E (PR #4).

## v1.0.2 — 2026-11-13

Security hardening (PR #1, integração OpenAI).

## v1.0.1 — 2026-11-12

Corrige a rolagem do menu lateral no mobile.

## v1.0.0 — 2026-11-11

Primeira versão publicada.
