# PROMPT MASTER KIRO — CICLO 1: AUDITORIA REAL DO RADAR LEILÃO

Você está trabalhando no repositório `jabesfelipe/radar-leilao`.

## MISSÃO

Preparar a execução da evolução integral do Radar Leilão até 100%, usando como fonte de verdade:
- `docs/ROADMAP-MASTER.md`
- `docs/PRODUCT-SCOPE-100.md`
- `docs/ACCEPTANCE-CRITERIA-MASTER.md`
- `docs/PROJECT-STATUS.md`
- `docs/PROJECT-HISTORY.md`
- `docs/TODO-PLATAFORMA-COMPLETA.md`
- documentos de arquitetura M0/B1 já existentes em `docs/`.

O usuário quer poucos prompts, mas entregas abrangentes e detalhadas. Portanto, faça uma auditoria profunda e produza um plano único, consolidado e executável para o Ciclo 2 e o Ciclo 3. Não transforme a auditoria em dezenas de perguntas ao usuário.

## REGRA DESTA EXECUÇÃO

**Executar somente o CICLO 1 — AUDITORIA E PREPARAÇÃO. Não implementar funcionalidades nesta execução.**

Não alterar código de aplicação, modelos, migrations, banco, dados, endpoints ou interface. Alterações documentais necessárias para registrar resultados são permitidas, append-only quando houver histórico.

## 1. BASELINE E PRESERVAÇÃO

Antes de qualquer ação:
1. Confirmar branch, commit HEAD, working tree e sincronização com origin.
2. Ler os documentos mestres e as especificações existentes.
3. Identificar como executar os testes sem alterar dados reais.
4. Registrar baseline das rotas/OpenAPI, migrations, testes e estrutura de módulos, quando tecnicamente possível.
5. Identificar ambiente e banco usado pelos testes; não conectar a ambiente produtivo.

Preservar obrigatoriamente:
- property 633 — COND PARQUE ARVOREDO RESIDENCIAL CLUBE;
- análises V1–V9;
- análises financeiras V1–V9;
- histórico de llm_runs;
- 27 canonical_key do Checklist Mestre;
- Central Jurídica e suas fontes/regras;
- documentos, versões, evidências, riscos, vereditos e histórico.

PROIBIDO:
- docker compose down -v;
- reset, truncate, drop, limpeza de volumes ou seed destrutivo;
- migrations ou backfill;
- criar V10 ou qualquer nova análise para property 633;
- executar LLM real, chamadas externas pagas ou scraping;
- alterar .env, segredos ou credenciais;
- modificar registros de negócio.

Se qualquer teste tiver risco de atingir banco persistente ou dados reais, não execute. Explique a limitação e proponha ambiente descartável.

## 2. AUDITORIA TÉCNICA COMPLETA

Inspecione o repositório real, não apenas a documentação.

### Backend
- módulos, serviços, modelos, schemas, rotas, dependências e middlewares;
- main.py e acoplamentos;
- engines determinísticos e agentes LLM;
- jobs, filas, tarefas agendadas e processamento assíncrono;
- autenticação/autorização, validação, erros e logs;
- integrações externas e variáveis de configuração.

### Banco e persistência
- tabelas e relacionamentos;
- migrations e head real;
- constraints, índices, cascades e unicidades;
- entidades que hoje dependem diretamente de property_id;
- compatibilidade de dados legados;
- armazenamento de arquivos, metadados, hashes e versões.

### Frontend
- rotas, páginas, tabs, hubs, componentes e serviços HTTP;
- jornadas que existem de fato;
- dashboards, filtros, formulários, estados vazios, loading e erro;
- acessibilidade e responsividade nos fluxos críticos.

### Inteligência e domínio
- captura e fontes de oportunidades;
- modalidades existentes e ausentes;
- documentos/OCR/extração/evidências;
- Central Jurídica, fontes e vigência;
- checklist e due diligence;
- riscos, veredito e hard stops;
- análise financeira, custos, valuation e comparáveis;
- aquisição, pagamentos, registro, posse, regularização;
- locação, venda e encerramento.

### Qualidade e operação
- testes unitários, integração, contrato e E2E;
- cobertura dos fluxos críticos;
- CI/CD e status de workflows;
- segurança, RBAC, auditoria e observabilidade;
- backup/restore e runbooks;
- performance e limites conhecidos.

## 3. MATRIZ REAL DE STATUS

Para cada requisito de `PRODUCT-SCOPE-100.md` e cada fase F0–F13, atribua exatamente um estado:
- NAO_INICIADO
- ESPECIFICADO
- EM_DESENVOLVIMENTO
- IMPLEMENTADO
- VALIDADO
- CONCLUIDO
- BLOQUEADO

Cada linha precisa conter:
- requisito/fase;
- status;
- evidência concreta (arquivo, classe, endpoint, migration, teste ou execução);
- o que já funciona;
- o que falta;
- dependências;
- riscos;
- critério de aceite pendente.

Não classifique como VALIDADO/CONCLUIDO com base apenas em documentação. Não invente percentuais. Separe:
- progresso de especificação;
- progresso de implementação;
- progresso de validação;
- progresso global ponderado.

Se não houver evidência, marque como NÃO AUDITADO ou ESPECIFICADO conforme o caso, explicando a diferença.

## 4. CONFRONTO E CORREÇÃO DOCUMENTAL

Compare o estado real com:
- PROJECT-STATUS;
- PROJECT-HISTORY;
- TODO-PLATAFORMA-COMPLETA;
- TODO-WORKFLOW-FOUNDATION;
- documentos M0/B1;
- ROADMAP-MASTER e PRODUCT-SCOPE-100.

Não apague histórico antigo. Registre divergências, datas e evidências. Aponte informações antigas que não representam mais o estado atual.

## 5. PLANO ÚNICO DO CICLO 2 E 3

Produza uma sequência executável de implementação com:
- ondas de entrega;
- dependências;
- arquivos/domínios impactados;
- migrations previstas (somente planejamento);
- riscos e mitigação;
- testes por onda;
- critérios de aceite;
- definição de pronto;
- estratégia para commits/PRs pequenos.

Agrupe trabalho para minimizar prompts futuros. O plano deve permitir que o usuário use um prompt abrangente para autorizar a construção e outro para validação final, sem perder controles internos.

Não faça alterações de código nesta etapa.

## 6. DOCUMENTOS DE SAÍDA

Criar/atualizar:
1. `docs/PROJECT-AUDIT-2026-11.md` — auditoria detalhada com evidências.
2. `docs/IMPLEMENTATION-PLAN-100.md` — plano único de implementação Ciclo 2 e validação Ciclo 3.
3. Atualizar `PROJECT-STATUS.md` com resumo executivo e status auditado.
4. Atualizar `PROJECT-HISTORY.md` append-only.
5. Atualizar `TODO-PLATAFORMA-COMPLETA.md` com status/evidências, sem apagar itens.
6. Atualizar `ROADMAP-MASTER.md` apenas se a auditoria revelar ajustes necessários, mantendo a visão de produto.

## 7. RELATÓRIO FINAL

Ao concluir, responder com:
- branch e commit auditados;
- working tree;
- estado de testes e comandos executados;
- baseline de migrations e OpenAPI;
- matriz F0–F13;
- percentual real, se calculável, e metodologia;
- principais gaps;
- dependências externas;
- plano consolidado do Ciclo 2 e 3;
- documentos alterados;
- confirmação explícita de que nenhum dado, análise, LLM ou serviço externo foi alterado/executado.

Não iniciar implementação. Encerrar aguardando autorização para o Ciclo 2.
