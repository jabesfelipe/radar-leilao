# PROMPT KIRO — RADAR LEILÃO | PLATAFORMA COMPLETA

## Objetivo
Evoluir o Radar Leilão de MVP/analisador para plataforma complexa, auditável e orientada a workflow, do intake à decisão de não participar ou à aquisição, registro, posse, regularização, reforma, locação e venda. Foco prioritário em leilões extrajudiciais, especialmente alienação fiduciária (Lei 9.514/1997), com fluxo judicial separado. Este documento é plano, não declaração de implementação.

## 1. Regras inegociáveis
- Evidência antes de conclusão. Ausência de resultado não é ausência de risco.
- Separar fato observado, documento, inferência, hipótese, estimativa e parecer.
- Conclusões materiais devem apontar fonte, documento/página/trecho, data-base, limitações, confiança e regra aplicada.
- Nenhuma automação garante segurança jurídica, registral, tributária ou financeira.
- Histórico append-only; correções criam nova versão e trilha before/after.
- GET, CRUD e navegação não podem disparar LLM, nova versão analítica ou custo externo incidentalmente.
- Reutilizar modelos, engines, tabelas, serviços e componentes atuais; não duplicar.
- Não executar scraping, consulta paga, automação externa ou integração sem autorização, credenciais e limites.
- Sistema apoia decisão; não substitui advogado, contador, registrador, engenheiro ou vistoria.
- Preservar 27 canonical_key, imóvel 633, histórico V1–V9 e baseline conhecida de 45 llm_runs. Não criar V10.

## 2. Fase zero obrigatória: diagnóstico antes de codificar
Ler README, PROJECT-STATUS, PROJECT-HISTORY, TODOs, specs, ADRs, migrations, arquitetura, modelos, endpoints, services, engines, frontend e testes. Mapear cadastro/leilão/fontes, documentos, matrícula/edital, Judicial API/DataJud, Checklist Mestre, Riscos/Veredito, Financeiro/Mercado, Ocupação, Due Diligence, Central Jurídica 0017, Pós-Arrematação 0015, eventos/histórico. Produzir matriz capacidade atual × gap × reuso × implementação × teste. Identificar divergências. Não presumir testes antigos. Não alterar imóvel 633 nem executar LLM/DataJud real.
Entregável: ROADMAP-PLATAFORMA-COMPLETA.md com arquitetura-alvo, mapa de gaps, dependências, migrations, testes e rollback. Apresentar plano incremental antes de mudanças estruturais.

## 3. Workflow alvo

### F0 Intake e descoberta
Capturar origem/URL, portal, identificador externo, credor, leiloeiro, modalidade, praça, datas, status, preço, avaliação, comissão, pagamento, endereço, matrícula e timestamp. Versionar snapshot e detectar mudanças de edital/preço/data/status. Deduplicar sem fundir registros ambíguos. Status: CAPTURADO, DUPLICADO_POTENCIAL, DADOS_INSUFICIENTES, EM_TRIAGEM.

### F1 Triagem/classificação
Classificar JUDICIAL, EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA, EXTRAJUDICIAL_OUTRA_GARANTIA, VENDA_DIRETA ou INDEFINIDO. Não inferir modalidade pelo termo “leilão”; exigir evidência no edital/ato. Aplicar regras conforme modalidade, UF/município, tipo de imóvel, ocupação e finalidade. Permitir prosseguir, pedir dados ou descartar com motivo.

### F2 Documentos/evidências
Cofre documental versionado: edital/retificações, matrícula atualizada/ônus, contrato/título disponível, notificações/intimações, avaliações, fotos, plantas, convenção/regimento, certidões, procurações, guias, comprovantes, auto/carta, registro, notificações de posse, contratos, recibos e notas. Metadados: emissor, origem, data, validade, período coberto, protocolo, hash, página, classificação, confidencialidade e versão. Nunca apagar documento substituído; usar supersedes. OCR deve guardar página/trecho, confiança e revisão. Campo não localizado = NAO_LOCALIZADO, nunca inventado.

### F3 Jurídico pré-leilão
Ler edital integral e retificações. Conferir matrícula: titularidade, alienação fiduciária, consolidação, cancelamentos, indisponibilidade, penhoras, hipotecas, usufruto, servidões, locação averbada, ações reais/reipersecutórias, restrições e averbações. Conferir cadeia registral e correspondência matrícula × edital × endereço × unidade × vaga × fração × área × cadastro. Verificar intimação para purgação da mora e demais atos exigidos com documento/data. Conferir consolidação e atos do art. 26/27 da Lei 9.514/97, alterações e transições. Pesquisar ações anulatórias, tutelas, recursos, disputas possessórias, inventário/família, falência/recuperação e execuções relevantes. Distinguir encontrado, homônimo, correlação provável e confirmada. Busca parcial/indisponível não pode retornar “sem processos”. Resultado: SEM_GAP_IDENTIFICADO_NAS_FONTES_CONSULTADAS, RISCO_CONTROLAVEL, PENDENCIA_RELEVANTE, RISCO_CRITICO, INVIAVEL ou INCONCLUSIVO, sempre com escopo e justificativa.

### F4 Fiscal/condomínio/operacional
IPTU, inscrição municipal, dívida ativa, exercícios, parcelamentos, certidão, sub-rogação e edital. Condomínio: declaração formal, períodos, principal, multa, juros, honorários, rateios, ações, acordos e data-base. Água/luz/gás: separar dívida pessoal de obrigação eventualmente vinculada ao imóvel. Certidões contextualizadas: distinguir imóvel, titular, devedor, credor e condomínio; registrar o que provam e o que não provam. Investigar zoneamento, tombamento, preservação, contaminação, desapropriação, regularidade de construção, habite-se, área divergente, cadastro e restrições condominiais.

### F5 Localização/inspeção
Geocodificação com fonte/precisão, sem tratar como confirmação cadastral. Avaliar acesso, transporte, comércio, escolas, saúde, infraestrutura, enchente, ruído, declividade e riscos ambientais. Vistoria: fachada, áreas comuns, ocupação, conservação, danos, padrão e fotos/vídeos datados. Sem vistoria interna, declarar limitação e contingência; Street View não prova estado interno.

### F6 Ocupação/posse
Classificar desocupado confirmado, proprietário/devedor, locatário, terceiro, incerto ou conflitante. Distinguir posse, propriedade, locação, comodato, usufruto e direitos de terceiros. Para locação, conferir contrato, prazo, averbação, preferência e regras. Oferecer contato respeitoso, proposta voluntária, notificação revisada, mediação, advogado e medida judicial. Proibir coerção, ameaça, exposição pública, corte de serviços, entrada forçada, troca de fechadura e retirada de bens sem autorização legal. Minutas são rascunhos para advogado. Ajuda de mudança/adiantamento exige consentimento livre, acordo escrito, aprovação, condições de pagamento, entrega de chaves, vistoria e quitação. Taxa de ocupação art. 37-A só pode ser calculada após validar incidência, beneficiário, marco inicial/final, base, cumulação e jurisprudência. Não presumir juros adicionais nem crédito garantido. Não prometer liminar.

### F7 Viabilidade financeira
Motor determinístico e explicável; cenários conservador/base/otimista. Incluir lance, comissão, ITBI, registro/escritura quando aplicável, certidões, emolumentos/FUNREJUS/fundos/selos conforme ato, tributos, condomínio, IPTU, débitos assumidos, advogado, desocupação, mudança, custas, reforma, regularização, seguro, utilidades, carregamento, custo de capital, corretagem e IR ganho de capital. Parâmetros por jurisdição/ato/base/fonte/vigência, não constantes eternas. Separar conhecido, estimado, cotação pendente e contingência. Evitar dupla contagem Auction/Costs/Debts/Pós. Calcular custo total, custo até regularização, custo de posse/reforma/saída, break-even, preço máximo, margem, ROI, TIR, fluxo de caixa e sensibilidade. IR depende de PF/PJ, regime e requisitos; exigir validação contábil.

### F8 Comitê/decisão
Score separado por jurídico, documental, físico, ocupação, fiscal, mercado, financeiro, liquidez e execução. Hard stops não podem ser mascarados por média. Exibir argumentos, incertezas, bloqueadores, pendências, preço máximo e validade temporal. Registrar decisão humana, responsável, data, justificativa e versão dos dados. Mudança de edital, preço, matrícula, processo, ocupação ou premissa invalida aprovação e exige revisão.

### F9 Lance/pagamento
Calendário, regras do portal, lance máximo aprovado, incrementos, comprovantes, horário, resultado. Vencedor: pagamento, comissão, guias, prazos, assinatura e documentos. Perdedor/cancelado/suspenso: encerrar com motivo. Não automatizar lances nem movimentar dinheiro sem autorização.

### F10 Transferência/registro
Reusar Pós-Arrematação. Auto/carta/termo, pagamento, ITBI, registro, exigências, prenotação, matrícula atualizada, baixa de ônus e titularidade. Conferir adquirente, fração, unidade e descrição. Separar pagamento, título e registro; não declarar propriedade registrada sem evidência registral.

### F11 Posse/regularização
Entrega voluntária/judicial, chaves, termo, vistoria, fotos, bens, medidores. Regularização municipal/registral/condominial, averbação, área, habite-se, cadastro e licenças. Reforma com escopo, orçamento, fornecedores, contratos, notas, medições, aditivos, cronograma e aceite; ART/RRT quando aplicável. Posse física não equivale a regularidade documental.

### F12 Exploração/saída
Estratégia venda, reforma e venda, locação ou manter. Locação: adequação, contrato, garantias, vistoria, administração, vacância, manutenção e tributos. Venda: avaliação, comparáveis, preço mínimo, corretagem, documentação, certidões, marketing, visitas, propostas, contrato, recebimento e registro. Comparar projetado × realizado: lucro, ROI, TIR, prazo e desvio.

### F13 Encerramento
Dossiê final exportável. Status: VENDIDO, LOCADO, MANTIDO, DESCARTADO, CANCELADO, PERDIDO_NO_LEILAO, ENCERRADO_COM_PENDENCIA. Retrospectiva e indicadores. Histórico não sobrescrito.

## 4. Central Jurídica 2.0
Cada norma: identificação oficial, artigo/parágrafo/inciso, texto oficial, link primário, publicação, vigência, alterações, redação histórica, contexto, fatos necessários, exceções, controvérsias, jurisprudência, orientação prática separada, evidências requeridas, efeito operacional/financeiro, confiança, revisor, data e próxima revisão. Separar verificação da fonte, vigência, transcrição, interpretação e aplicação. Aplicabilidade: APLICAVEL, APLICAVEL_CONDICIONAL, APENAS_REFERENCIA, NAO_APLICAVEL, INDETERMINADO.
Investigar Lei 9.514/97 e alterações; CC; CPC no fluxo judicial; Lei 8.245/91; CTN; Lei 6.015/73; emolumentos, CNJ e Corregedoria; Lei 4.591/64; Lei 13.465/17; normas urbanísticas, ambientais, estaduais e municipais; jurisprudência STF/STJ/TJs. Priorizar Planalto, Diário Oficial, tribunais, CNJ, órgãos fiscais e Corregedorias. Site privado é pista, não fonte final. Nunca inventar julgado ou texto não conferido.

## 5. Revisão das anotações
Usar como backlog, não verdade pronta:
- Biasi, Globo Leilões, Bidmap, Spy Leilões: diretório de portais; validar legitimidade, cobertura, termos, acesso e API; sem scraping não autorizado.
- Registro24/RI Digital: validar oficialidade, cobertura, custo, autorização.
- RTD/notificação: validar serviço, prova de entrega e requisitos; minuta por advogado.
- Usufruto: alerta crítico; óbito alegado não basta para presumir extinção; conferir certidão, registro e cancelamento.
- IR 15%, reinvestimento em 180 dias e redutores por tempo: não fixar nem prometer; validar PF/PJ, regime, requisitos e legislação.
- FUNREJUS 0,2% e teto anotado, ISSQN, FUNDEP e selo: não cadastrar sem tabela oficial atual, ato, base e vigência; evitar duplicidade.
- Água/luz/gás: separar dívida pessoal de obrigação vinculada.
- Certidões: matriz contextual; negativa não garante imóvel livre.
- Preço vil 50%: avaliar no judicial; não usar como piso universal extrajudicial.
- Inquilino/liminar: validar contrato, averbação, modalidade e pressupostos; não prometer liminar.
- Negociação/ajuda de mudança: voluntária, documentada, aprovada e condicionada.
- Taxa de ocupação 1%: validar art. 37-A, incidência, marco, base, legitimidade e jurisprudência; não presumir juros cumulados.
- Honorários/custas: estimativas por fase/jurisdição e cotações; sem ameaça ao ocupante.
- Fotos/vídeos: origem, data, legitimidade e limites.

Portais/serviços potenciais anotados: https://www.biasileiloes.com.br/ ; https://globoleiloes.com.br ; https://bidmap.com.br ; https://www.spyleiloes.com.br ; https://www.registro24.com.br/ ; https://www.rtdbrasil.org.br/ ; https://desocupacaoleiloes.com.br/ ; https://desocupasimples.com.br ; https://www.mestredosleiloes.com/ . Validar antes de integrar. Instagram/Drive não são fonte normativa.

## 6. Checklists
Preservar 27 canonical_key; não renomear/remover sem migração compatível. Expandir por fase, modalidade, tipo, UF/município, ocupação, finalidade e risco. Cada item: pergunta verificável, objetivo, aplicabilidade, criticidade/hard stop, evidência mínima, fonte, responsável, prazo/validade, critérios de aprovação/reprovação/inconclusivo, dependências, impacto e versão. Estados: NAO_INICIADO, PENDENTE_DOCUMENTO, EM_VALIDACAO, CONFIRMADO, NAO_CONFIRMADO, NAO_APLICAVEL_JUSTIFICADO, DIVERGENTE, VENCIDO, BLOQUEADO, REVISAR. “Não encontrado” exige fonte, escopo, data, parâmetros e limitações. NAO_APLICAVEL exige justificativa. Auditar cobertura, duplicidade, conflito e itens vagos.

## 7. Arquitetura, segurança e IA
Reusar FastAPI/PostgreSQL/SQLAlchemy/Alembic/React/TypeScript. Antes de nova tabela, demonstrar que entidade existente não atende e documentar ADR. Integrações com timeout, retry limitado, rate limit, cache/validade, idempotência e logs sem segredo. Guardar source, retrieved_at, valid_at, confidence, coverage, limitations e evidence_ids. Versionar regras, checklists, motores e decisões. LGPD: minimização, acesso, retenção, mascaramento e trilha. Segurança de upload, SSRF, prompt injection, XSS, RBAC e segredos.
LLM só para extração/síntese; cálculo/gates determinísticos. Toda resposta LLM cita documento/página/trecho/fonte/confiança. Documento é dado não confiável. Validar saída por schema e revisão humana. Nunca inventar jurisprudência, artigo, certidão ou mercado. Custos IA por imóvel/fase/documento/agente.

## 8. UX
Dashboard de pipeline e próximos passos. Dossiê com progresso por fase, status, evidências, base legal, custos, responsáveis e prazos. Em cada checklist: por que importa, o que conferir, base legal, evidências, risco e próxima ação. Exibir “por que recomenda?”. Hard stops separados de score. Semáforo com legenda. Wizard simples, campos avançados progressivos, checklist progressivo e visão completa auditável. Responsivo e acessível.

## 9. Testes e aceite
Unitários, integração PostgreSQL, migrations upgrade/downgrade, API, autorização, idempotência, falhas de integração, TypeScript/Vitest, E2E quando disponível, fixtures judicial/extrajudicial, dados incompletos/divergentes/homônimos, fontes indisponíveis, canonical_key, GET/CRUD não disparar LLM, imutabilidade, segredos, cálculos financeiros e sensibilidade. Nunca declarar E2E sem evidência.
Aceite: risco crítico não escondido por score; conclusão tem evidência ou incerteza; regimes separados; checklists versionados; custos com fonte/vigência; decisão reproduzível; workflow do intake ao encerramento; próximos passos claros; integração desconfigurada nunca aparece como sucesso; histórico imutável.

## 10. Épicos
A Diagnóstico; B Workflow/gates; C Evidências/documentos; D Checklists dinâmicos; E Central Jurídica 2.0; F Due Diligence; G Ocupação/posse; H Financeiro; I Comitê/lance; J Pós-arrematação/registro; K Reforma/locação/venda; L Relatórios/auditoria; M Integrações oficiais/segurança/observabilidade. Cada épico: spec, ADR, tarefas pequenas, dependências, migration reversível, testes, documentação, aceite, rollback e evidência.

## 11. Restrições
Não executar down -v, reset, truncate, drop ou seed destrutivo. Não sobrescrever .env/segredos. Não executar LLM no imóvel 633 nem criar V10. Não executar DataJud real, consulta paga, scraping ou lance. Não alterar canonical_key. Não migrar sem backup/rollback. Não marcar teste sem log. Não afirmar “100% seguro”. Antes de mudanças centrais, apresentar impacto. Commits pequenos sem scratch/secrets; preferir branch/PR para código.

## 12. Entregáveis iniciais
- docs/ROADMAP-PLATAFORMA-COMPLETA.md
- docs/WORKFLOW-LEILAO-END-TO-END.md
- docs/MATRIZ-CHECKLIST-MODALIDADE.md
- docs/MATRIZ-CURADORIA-JURIDICA.md
- docs/MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS.md
- docs/REVISAO-ANOTACOES-LEILAO.md
- docs/TODO-PLATAFORMA-COMPLETA.md
- Atualizar PROJECT-STATUS, PROJECT-HISTORY e TODO-CENTRAL-JURIDICA.

Comece somente pelo diagnóstico e documentação. Apresente matriz de gaps e plano incremental antes de implementar o workflow inteiro.
