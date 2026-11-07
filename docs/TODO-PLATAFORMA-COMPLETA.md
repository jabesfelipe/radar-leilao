# TODO — Plataforma completa Radar Leilão

Backlog planejado, não declaração de funcionalidades implementadas. Ver docs/PROMPT-KIRO-PLATAFORMA-COMPLETA.md.

## P0 — Diagnóstico, integridade e segurança
- [ ] Diagnóstico de módulos, tabelas, endpoints, migrations, engines e testes.
- [ ] Matriz capacidade atual × gap × reuso × implementação × testes.
- [ ] Separar judicial, extrajudicial/alienação fiduciária, outras garantias e venda direta.
- [ ] Estados explícitos de incerteza; ausência de resultado não é ausência de risco.
- [ ] Matriz de evidências com fonte, data, validade, abrangência, página/trecho, hash, confiança e limitações.
- [ ] Hard stops que score não possa mascarar.
- [ ] Preservar 27 canonical_key, imóvel 633, V1–V9 e baseline conhecida de 45 llm_runs.
- [ ] GET/CRUD/navegação não criam análise LLM, versão ou custo externo.
- [ ] Segurança, RBAC, LGPD, segredos, auditoria, retenção e proteção documental.

## P0 — Central Jurídica
- [ ] Conferir fonte primária, redação vigente/histórica e alterações.
- [ ] Separar verificação da fonte, vigência, transcrição, interpretação e aplicação.
- [ ] Aplicabilidade por modalidade, etapa, jurisdição e fatos.
- [ ] Revisar Lei 9.514/97 arts. 26, 27 e 37-A, alterações e transições.
- [ ] CPC/arrematação judicial separado do extrajudicial.
- [ ] Revisar CTN 130/131 e condomínio em trilhas próprias.
- [ ] Revisar locação, preferência, denúncia, averbação, usufruto e direitos reais.
- [ ] Jurisprudência somente com número, órgão, tese, data, situação e fonte oficial.
- [ ] Recuperar “136 + 27 → 45 regras”; não fabricar conteúdo.
- [ ] Auditar cobertura dos 27 canonical_key.
- [ ] Registrar revisor, data, próxima revisão e histórico de alterações.

## P1 — Workflow
- [ ] F0 intake, origem, snapshot, deduplicação e qualidade.
- [ ] F1 triagem/classificação inequívoca.
- [ ] F2 cofre documental versionado e OCR com página/trecho.
- [ ] F3 análise jurídica registral, edital, intimação, consolidação e processos.
- [ ] F4 diligência fiscal, condominial, serviços, certidões e urbanismo.
- [ ] F5 inspeção física, localização, entorno e limitações.
- [ ] F6 ocupação, locação, posse, negociação voluntária e estratégia judicial.
- [ ] F7 motor financeiro completo, cenários, preço máximo, fluxo e sensibilidade.
- [ ] F8 comitê, hard stops e aprovação humana.
- [ ] F9 calendário, lance, pagamento, comissão e resultado.
- [ ] F10 transferência, título, ITBI, registro e matrícula atualizada.
- [ ] F11 posse, regularização e reforma.
- [ ] F12 venda/locação/holding e resultado realizado.
- [ ] F13 encerramento, dossiê e retrospectiva.

## P1 — Checklists
- [ ] Preservar 27 canonical_key.
- [ ] Checklist por modalidade, fase, tipo, jurisdição, ocupação, finalidade e risco.
- [ ] Cada item com pergunta verificável, finalidade, evidência, critério, fonte, criticidade, responsável e validade.
- [ ] Estados: NAO_INICIADO, PENDENTE_DOCUMENTO, EM_VALIDACAO, CONFIRMADO, NAO_CONFIRMADO, NAO_APLICAVEL_JUSTIFICADO, DIVERGENTE, VENCIDO, BLOQUEADO, REVISAR.
- [ ] “Não encontrado” exige escopo de consulta; NAO_APLICAVEL exige justificativa.
- [ ] Auditoria de cobertura, duplicidade, conflito e itens vagos.

## P1 — Custos/tributos
- [ ] Parametrizar por jurisdição, ato, base, vigência e fonte oficial.
- [ ] Validar ITBI, registro, escritura, emolumentos, FUNREJUS, fundos e selos.
- [ ] Validar IPTU, condomínio, consumo, custas, honorários, mudança, reforma, carregamento e saída.
- [ ] IRPF/IRPJ e ganho de capital conforme regime e requisitos.
- [ ] Validar regra dos 180 dias e redutores sem generalização.
- [ ] Evitar dupla contagem Auction/Costs/Debts/Pós.
- [ ] Memória de cálculo, fonte, data-base e incerteza.

## P1 — Ocupação/posse
- [ ] Classificar ocupante e fundamento sem inferência sensível desnecessária.
- [ ] Mapear propriedade, posse, locação, usufruto, comodato e direitos.
- [ ] Negociação voluntária documentada, aprovada e condicionada.
- [ ] Minutas respeitosas revisadas por advogado; sem ameaça/coerção.
- [ ] Simulador taxa ocupação após validar incidência, base, período e legitimidade.
- [ ] Workflow de advogado/processo/custas/prazos estimados sem prometer liminar.
- [ ] Bloquear autotutela, corte de serviços, entrada forçada e retirada de bens.

## P2 — Integrações/IA/UX
- [ ] Validar portais/serviços anotados, termos, API, autorização, custo e cobertura.
- [ ] Fontes oficiais autorizadas para registro, prefeitura, tribunais, certidões e mapas.
- [ ] RAG com documentos versionados e citações por página/trecho.
- [ ] Limites de custo por imóvel/fase/documento e controle de execução.
- [ ] Dashboard, próximos passos, dossiê, explicação das recomendações e relatórios.
- [ ] Indicadores projetado × realizado, descarte, ROI, tempo de posse e desvios.
- [ ] Revisão periódica de regras, checklists, fontes e parâmetros.

## P0 — Testes e preservação
- [ ] Unitários, PostgreSQL integração, API, frontend e E2E quando disponível.
- [ ] Migrations upgrade/downgrade e rollback.
- [ ] Fixtures judicial/extrajudicial e casos incompletos/divergentes/homônimos.
- [ ] Não regressão canonical_key e histórico.
- [ ] GET/CRUD não executa LLM.
- [ ] Nunca declarar E2E sem evidência.
- [ ] Nenhum reset ou alteração do imóvel 633 sem autorização.
