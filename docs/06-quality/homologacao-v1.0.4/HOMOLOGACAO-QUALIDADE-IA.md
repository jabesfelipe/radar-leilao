# Homologação v1.0.4 — qualidade da IA, extração documental e rastreabilidade

Origem: primeira execução completa com a OpenAI real (v1.0.3, caso sintético `caso-01`, 14/11/2026). A integração
funcionou (5 agentes, embeddings, RAG, supervisor, orçamento), mas a qualidade das informações que alimentam a decisão
tinha problemas. Esta versão corrige as causas raiz sem mudar a arquitetura nem a decisão financeira determinística.

Dados 100% sintéticos. Nenhum documento real, chave ou dado pessoal neste documento.

## 1. Problemas da 1ª execução e causas raiz

| # | Problema observado | Causa raiz (código) |
|---|---|---|
| 1 | Extração da matrícula (`registration_number`) e do edital (`notice_date`) rejeitada: "Campo extraído sem referência correspondente"; chamadas cobradas e descartadas | `extraction.validate_extraction_references` comparava `str(valor)` com o `value` da referência por **igualdade exata**: `date(2024,10,10)` → `"2024-10-10"` contra "10 de outubro de 2024"; "99.901" contra "nº 99.901". Um único campo derrubava a extração inteira. E o trecho citado (`excerpt`) **nunca** era conferido contra o documento |
| 2 | Números do snapshot financeiro ("ROI −7,78%", "resultado líquido R$ −26.550", "preço médio R$ 329.466,67") apareciam como "trecho literal" do `edital.txt` | `services.persist_agent_findings` gravava `evidence_excerpt` do modelo sem validar e, para agentes não documentais, usava `chunk.content[:1000]` de qualquer chunk citado como "trecho literal". O agente financeiro cita o chunk do edital e a evidência herdava o documento |
| 3 | Pergunta do checklist apresentada como trecho literal ("A vaga de garagem possui matrícula própria?") | `persist_checklist_agent_findings` aceitava o `evidence_excerpt` do modelo sem conferir que ele existe no chunk |
| 4 | 19 citações fracas (cobertura < 30%) | Combinação de 2 e 3: afirmação sem relação com o chunk citado era persistida como evidência documental |
| 5 | 10 itens do checklist fora de PENDENTE "sem evidência" | Parte era **medição**: o roteiro `valor_negocio.py` procurava o vínculo em `evidence_links` com `target_type 'checklist%'`, que o produto não usa (o vínculo fica em `checklist_evidences`). Parte era real: o estado mudava com qualquer chunk citado, mesmo sem sustentar a afirmação, e sem registro da origem da resolução |
| 6 | Fatos não encontrados: comissão de 5% + pagamento à vista (F7), venda *ad corpus* (F9), valores do 2º leilão (F8), divergência de área (F6) | **Não era RAG**: os 4 chunks do imóvel A estavam no contexto dos agentes. O prompt do agente documental era genérico. F6 exige dois documentos (62 m² na matrícula, 68 m² no edital): com uma evidência por chunk, o roteiro de pontuação não consegue contá-lo como "com evidência" (limitação da medição, ver §6) |
| 7 | (achado nesta homologação) Extração sem busca vetorial rodava com contexto vazio | A consulta textual literal `"matricula"` podia não casar nenhum chunk; a chamada ao modelo era feita mesmo assim |
| 8 | (achado nesta homologação) Com `LLM_MAX_OUTPUT_TOKENS=1500` o agente jurídico estourou o limite de saída | Até 12 findings com trechos de 240 caracteres não cabiam; resposta truncada = chamada cobrada e descartada (o supervisor registrou `AGENTES_PARCIAIS`, 4/5, sem esconder a falha) |
| 9 | (achado nesta homologação) Teto por análise sem teto mensal não bloqueava modelo sem preço | `build_gateway` só checava preço em `llm_pricing` quando `LLM_BUDGET_USD_MONTH` existia; sem preço o custo é `None` e o teto por análise nunca dispara |

## 2. Correções

| Frente | Alteração | Arquivos |
|---|---|---|
| Validação de citações | Novo módulo: trecho informado precisa ser cópia (normalizada: acentos, caixa, aspas, espaços, quebras de linha, reticências em ordem) do chunk; valores da afirmação precisam estar no chunk (percentuais calculados pelo modelo não contam como prova); pergunta do checklist/prompt nunca vale como trecho. Força: FORTE, MODERADA (trecho derivado do próprio documento), FRACA, INVALIDA. Só FORTE/MODERADA são prova | `backend/app/citations.py` |
| Extração estruturada | Cada campo é validado contra o texto do documento (datas e valores em qualquer grafia brasileira, identificadores pelos dígitos); referência com chunk de outro documento, página inexistente, trecho ausente ou trecho que não contém o valor é rejeitada. Campo inválido é **descartado** (INCONCLUSIVO, com motivo) e os válidos são preservados. Situação por campo: EXTRAIDO / NAO_ENCONTRADO / INCONCLUSIVO; da extração: CONCLUIDA / NAO_ENCONTRADO / INCONCLUSIVA / SEM_TEXTO / ERRO. Documento sem texto não chama o provider. Contexto da extração com termos do tipo de documento e fallback para os trechos do próprio documento | `backend/app/extraction.py`, `main.py` (resposta de `/extrair` ganha `status_extracao` e `campos`; `status` mantido) |
| Origem das evidências | Colunas `origin`, `strength`, `agent` em `evidences` e `resolution_origin` em `checklist_results` (migration 0025, idempotente, colunas opcionais). Evidência com documento só com citação FORTE/MODERADA e trecho da fonte; dado do snapshot fica CALCULO/CADASTRO sem documento; o resto é INFERENCIA_IA (confiança BAIXA, vínculo `MENCIONA`). Pesquisa judicial marcada `PESQUISA_JUDICIAL` | `models.py`, `migrations/versions/0025_evidencia_origem_forca.py`, `services.py`, `evidence.py`, `judicial_integration.py` |
| Checklist | Item só muda de estado com evidência documental FORTE/MODERADA (agente de checklist ou outro agente); regra determinística registra `REGRA_DETERMINISTICA`. API do imóvel expõe `resolution_origin` e `evidence_ids` por item. Estados existentes preservados (sem novos estados): sem evidência suficiente o item permanece PENDENTE | `services.py`, `main.py` |
| Agentes | Regras de origem comuns (`source` = documento/cadastro/calculo/inferencia, trecho literal, sem cálculos próprios em fatos, no máximo 8 findings curtos); roteiro de pontos do agente documental (ônus, ocupação, débitos, área por documento, valores do leilão, pagamento + comissão, condições de venda). Contrato `Finding` ganha `source` opcional | `ai/prompts.py`, `ai/agents.py`, `ai/contracts.py` |
| Orçamento | Modelo sem preço falha fechado também com só o teto por análise | `ai/budget.py`, `ai/gateway.py` |
| Interface | Evidência mostra origem ("Fato do documento", "Cálculo do Radar", "Informação cadastrada", "Inferência da IA") e força ("Evidência forte", "Citação fraca — não comprova"); cálculo e inferência nunca aparecem como trecho de documento. Registros antigos sem origem continuam exibidos como antes | `frontend/src/pages/VerdictSection.tsx`, `services/assessment.ts`, `styles.css` |
| Medição | `valor_negocio.py`: vínculo do checklist lido de `checklist_evidences`; novas métricas (origem/força, pergunta como trecho, valor ausente do documento citado, situação por campo da extração). **Gabarito e regras de pontuação inalterados** | `e2e/valor-negocio/valor_negocio.py` |

| Confronto documental | Matrícula × edital do mesmo imóvel, determinístico (sem IA): área privativa e número da matrícula, com valor, documento, chunk e trecho de cada lado; resultado CONFERE / DIVERGENCIA / NAO_COMPARAVEL e orientação de validação (divergência não é irregularidade presumida). Exposto em `GET /api/imoveis/{id}` (`confronto_documental`) e na seção Veredito | `backend/app/document_comparison.py`, `main.py`, `VerdictSection.tsx` |
| Provider | `with_structured_output(..., method="function_calling")`; contrato dos agentes e da extração tolerante a variações de forma (`source`, `kind`, confiança, `chunk_ids`, valor numérico na referência) sem relaxar a validação de conteúdo | `ai/providers/openai_provider.py`, `ai/contracts.py`, `extraction.py` |
| Privacidade | CPF só com dígitos e sem rótulo passa a ser mascarado (somente com dígitos verificadores válidos). Teste do que **chega ao provider** (extração e gateway) com CPF formatado/sem formatação, RG, e-mail, telefones, conta bancária e nome de pessoa física | `privacy.py`, `tests/test_privacy_payload.py` |
| Orçamento persistente | `LLM_REQUIRE_BUDGET` (falha segura sem os dois limites); `docker-compose.prod.yml` liga por padrão; `.env.prod.example` traz 0,50/mês, 0,10/análise, 1500 tokens de saída; `.env` local recebeu os mesmos valores (arquivo não versionado; chave intocada) | `config.py`, `ai/gateway.py`, `ai/budget.py`, `docker-compose.prod.yml`, `.env.prod.example` |

Decisões:

- **Sem nova tentativa automática** na extração: a validação por campo já preserva o que foi comprovado; uma segunda
  chamada dobraria o custo sem garantia. O motivo de cada rejeição fica na resposta e no evento `*_EXTRAIDA`.
- **Sem novos estados de checklist**: "inconclusivo" = permanece PENDENTE; o requisito "não confundir ausência com
  confirmação" é atendido sem alterar o contrato dos estados.
- **Normalização, não paráfrase**: o validador aceita diferenças de formatação, nunca sinônimos. Valores escritos de
  outra forma ("R$ 37,5 mil" × "R$ 37.500,00") são tratados como ausentes do documento (falso negativo aceito: preferimos
  rebaixar uma citação verdadeira a aceitar uma falsa).
- **Motor financeiro inalterado**: as regras pedidas (desconhecido ≠ zero, otimista só prova inviabilidade, FAVORÁVEL
  só com cálculo completo, ausência de IA ≠ inviabilidade) já estavam em `verdict_engine.py` desde a v1.0.2 e foram
  revalidadas pelo caso-01 (§4).

## 3. Testes

| Suíte | Resultado |
|---|---|
| Backend completo (PostgreSQL 16 + pgvector, `alembic upgrade head` até 0025) | **1205 passed, 3 skipped, 0 failed** (v1.0.3: 1124 passed, 3 skipped — os mesmos 3 skips, já existentes) |
| Novos: `test_citations.py`, `test_extraction_references.py`, `test_evidence_traceability.py`, `test_budget_pricing.py`, `test_document_comparison.py`, `test_privacy_payload.py`, `test_agent_contract_tolerance.py` | incluídos acima (extração com/sem número e data, página inexistente, trecho inexistente, documento errado, resposta malformada e incompleta, sem texto, falha de conexão; checklist com evidência, por regra, sem evidência, inválida, de outro imóvel, inconclusivo, não aplicável; snapshot financeiro nunca atribuído ao edital; isolamento A/B) |
| Frontend: `tsc -b`, vitest, `vite build` | 0 erros; **182 passed** (29 arquivos); build OK |
| E2E Playwright (desktop/mobile) | **não reexecutado** nesta versão (exige backend + frontend dev rodando; ver pendências) |

Testes existentes ajustados (intenção preservada, rigor maior): `test_extraction.py` (as referências agora precisam
existir no texto do chunk; um `MonkeyPatch` avulso que vazava o RAG falso para outros testes passou a usar a fixture),
`test_legal_agent.py` e `test_rag_isolation.py` (o trecho do chunk agora sustenta a afirmação do controle positivo),
`test_migration_0024.py` (alvo explícito `0024`, já que existe a 0025).

## 4. OpenAI real — caso-01 antes × depois

Antes: v1.0.3 (relatório `20261114-092611`). Depois: v1.0.4, última execução completa (`20261114-104253`, provider com
function calling) e verificação real dirigida da extração (mesmo banco sintético, sem persistir). Gabarito inalterado.

| Indicador | Antes (v1.0.3) | Depois (v1.0.4) |
|---|---|---|
| Fatos do gabarito (pontos) | 14/20 | **15/20** (F1–F5 e F8 com evidência; F6 e F7 mencionados sem evidência num único chunk; F9 não encontrado) |
| Fatos críticos (penhora, indisponibilidade, ocupação) | 3/3 | 3/3 |
| Citações válidas (critério do roteiro) | 62% | **100%** |
| Citações fracas (T6) | 19 | **0** |
| Pergunta do checklist como trecho literal | ≥ 2 (ex.: evidência #52) | **0** |
| Dado do snapshot atribuído a documento | ~15 (financeiro/mercado citando o edital) | **0** (14 evidências agora com origem `CALCULO`, 3 `CADASTRO`, sem documento) |
| Evidência documental com citação fraca/inválida | não medido | **0** (12 evidências `DOCUMENTO`: 11 FORTE, 1 MODERADA) |
| Armadilhas T1–T5 (valor inventado, "livre de ônus", FGTS, processo inexistente, "desocupado") | 0 | 0 |
| Extração da matrícula | ERRO (rejeitada inteira) | **CONCLUIDA**: número 99.901, cartório, comarca, data da certidão e titular, cada um com trecho e chunk |
| Extração do edital | ERRO | **CONCLUIDA** na verificação dirigida (etapa, avaliação, lance mínimo, data do leilão, leiloeiro); `notice_date` rejeitada por ponteiro de chunk errado — causa corrigida depois (teste `test_documento_com_mais_de_um_trecho_corrige_chunk_id_errado`) |
| Itens do checklist fora de PENDENTE | 10 (vínculo não verificável; LANCE_MENOR_50 resolvido pela IA) | 2 por regra determinística nesta execução; na execução `103210`, 4 pela IA com evidência FORTE + 1 por regra. Nenhum item sem origem |
| Confronto de área matrícula × edital | inexistente | **DIVERGÊNCIA 62,00 × 68,00 m²** com as duas fontes (determinístico, `test_caso01_divergencia_de_area_com_as_duas_fontes`) |
| Veredito | DESFAVORÁVEL / NÃO ARREMATAR | DESFAVORÁVEL / NÃO ARREMATAR (preço máximo R$ 136.266, prejuízo R$ 26.550, margem −7,9% — iguais ao gabarito) |
| Isolamento A × B | OK | OK (400 na extração cruzada, 404 na evidência cruzada, nenhum chunk cruzado) |
| CPF / segredo em log ou `llm_runs` | não / não | não / não; chave: 0 ocorrências em 107 arquivos de log/saída, relatórios e cópia do backend |
| Custo do roteiro completo (A + controle B + extrações) | US$ 0,0112 | **US$ 0,0079** |
| Custo da análise do imóvel A (5 agentes) | US$ 0,0061 | US$ 0,0046 (tokens 18.645 entrada / 3.033 saída) |
| Tempo do roteiro / `/analisar` de A | 142,7 s / 65,9 s | 75,6 s / 38,2 s |

Custo por agente na análise de A (`104253`): documental US$ 0,00088 · jurídico 0,00106 · financeiro 0,00081 · mercado
0,00071 · checklist 0,00116.

Variabilidade observada entre execuções (mesmo código, mesmo documento): 12 a 15 pontos; itens de checklist resolvidos
pela IA de 0 a 4. As métricas de rastreabilidade (citações válidas 100%, T6 0, pergunta como trecho 0) se mantiveram em
todas as execuções após a correção.

Achados da própria homologação, corrigidos e testados (em ordem): resposta truncada pelo limite de saída (causa: modo
`json_schema` estrito do LangChain; agora `method="function_calling"`, com uma única nova tentativa mínima e o custo das
duas chamadas registrado); referências com `field="property_id"` (contexto da extração tinha metadados do RAG); trecho
certo com `chunk_id` errado; marcador `[CPF]` copiado no trecho; `source`/`value` fora do tipo esperado derrubando a
resposta inteira (normalização no contrato); IA respondendo item calculado (`LANCE_MENOR_50_AVALIACAO`).

Custo total da homologação (todas as execuções, testes de bloqueio e diagnósticos, somando `llm_runs` dos bancos de
teste e as chamadas diretas de diagnóstico): **≈ US$ 0,08**, dentro do teto temporário de US$ 0,50 do processo. Duas
execuções foram contaminadas por disparo duplicado do terminal (descartadas da medição; ver §7).

## 5. Orçamento e custos

- Configuração do teste (somente no processo local; o `.env` não foi alterado): `LLM_PROVIDER=openai`,
  `LLM_MODEL=gpt-4o-mini`, `EMBEDDING_MODEL=text-embedding-3-small`, `LLM_BUDGET_USD_PER_ANALYSIS=0.10`,
  `LLM_BUDGET_USD_MONTH=0.50` (teto temporário do teste), `LLM_MAX_OUTPUT_TOKENS=1500`, `LLM_REDACT_PII=true`.
- O teto da aplicação **não substitui** o limite rígido do painel da OpenAI.
- O que entra no orçamento: tokens reais de entrada e saída de chat (agentes e extração, inclusive respostas inválidas
  já cobradas), embeddings com tokens **estimados** (caracteres/4). Retries internos do SDK (`LLM_MAX_RETRIES=1`) podem
  cobrar uma chamada duas vezes sem a aplicação ver. O teto por análise é verificado **antes** de cada agente e pode ser
  ultrapassado em no máximo uma chamada (observado no teste de bloqueio: com teto de US$ 0,001, um ou dois agentes rodam).
  A extração documental não entra no teto por análise (é uma operação separada), mas entra no mensal.

## 6. Limitações e riscos conhecidos

- **F6 (divergência de área)** envolve dois documentos; o roteiro de pontuação exige um único chunk com "62" e "68" e
  por isso não consegue contar o fato como "com evidência" mesmo quando o Radar registra as duas áreas com seus trechos.
  O gabarito não foi alterado.
- A validação de citações é léxica; uma afirmação errada que reaproveite as palavras do trecho certo pode passar como
  MODERADA. Revisão humana continua necessária antes de decidir.
- Com o validador mais estrito, parte das afirmações do modelo vira "Inferência da IA" em vez de evidência: é
  intencional (menos afirmações, todas rastreáveis).
- Privacidade: o gateway continua mascarando CPF/RG/e-mail/telefone/dados bancários e pseudonimizando pessoas físicas
  antes de qualquer envio; endereço, número da matrícula, número de processo e nomes de pessoas jurídicas continuam sendo
  enviados porque são necessários à análise jurídica. Retenção da OpenAI: política padrão da API.
- **HTTPS (bloqueador para documento real):** a configuração de produção do repositório publica o proxy só na porta
  80 (`docker-compose.prod.yml`, modo A "HTTP sem TLS"); o template `docker/nginx-proxy.conf` com 443 não é o usado pelo
  compose de produção. O procedimento completo (Tailscale ou domínio + Let's Encrypt, cookie `Secure`, `REQUIRE_HTTPS`)
  está em [docs/04-operations/https-ocr-monitoramento.md](../../04-operations/https-ocr-monitoramento.md) — documentado,
  **não aplicado**.
- **Estado real da VPS de homologação (inspeção somente leitura, 14/11/2026, nada alterado):** v1.0.3 com 5 contêineres
  saudáveis; proxy em `0.0.0.0:80`, `ALLOW_PUBLIC_HTTP=1`, só a porta 80 escutando; de fora, `http://<VPS>/` responde 403
  (portão) e `https://<VPS>/` não responde; sem certificado, sem Tailscale; `REQUIRE_HTTPS` vazio; `LLM_BUDGET_*` vazios;
  `OPENAI_API_KEY` **não definida** (a IA não pode ser chamada na VPS hoje). Para concluir o HTTPS falta **um** de: (a) um
  domínio apontado para a VPS (Let's Encrypt), ou (b) autorizar a VPS na conta Tailscale do responsável (`tailscale up`
  abre um link de login; ou fornecer uma auth key de uso único). Certificado autoassinado no IP não foi adotado: não
  protege contra interceptação sem distribuição manual do certificado. Ao implantar a v1.0.4, o compose já liga
  `LLM_REQUIRE_BUDGET=true`: sem os limites no `.env.prod`, a IA fica bloqueada (falha segura).

## 7. Procedimentos

**Análise sintética com IA real (local, nunca produção):** backend local com a chave apenas no ambiente do processo e os
limites acima; depois

```bash
~/radar-venv/bin/python e2e/valor-negocio/valor_negocio.py --api http://127.0.0.1:8100 \
  --db postgresql://postgres@127.0.0.1:54329/<banco_local> --log <stdout do backend>
```

O relatório fica em `e2e/results/valor-negocio/<data>/relatorio.{json,md}` (ignorado pelo Git).

**Diagnóstico de uma análise:** ver [VALIDACAO-E-DIAGNOSTICO.md](../homologacao-v1.0.2/VALIDACAO-E-DIAGNOSTICO.md) §3;
`llm_runs` traz agente, modelo, tokens, custo, status e motivo de bloqueio por chamada.

**Execução controlada:** uma execução por vez (o script de validação usa `flock`). Duas execuções simultâneas contra o
mesmo backend/banco contaminam a medição (aconteceu nesta homologação e as execuções foram descartadas).

**Como ler evidência e veredito:**

- "Fato do documento" + "Evidência forte/moderada": trecho literal conferido no documento do próprio imóvel.
- "Cálculo do Radar" / "Informação cadastrada": vem do motor ou do cadastro, não de documento.
- "Inferência da IA" ou "Citação fraca/inválida": não comprova; validar antes de decidir.
- O veredito é do motor determinístico (`verdict_engine.py`); a IA fornece fatos e pendências, nunca a decisão.
- Extração: `status_extracao` e `campos` dizem, por campo, se foi extraído, não consta ou foi descartado (com motivo).
