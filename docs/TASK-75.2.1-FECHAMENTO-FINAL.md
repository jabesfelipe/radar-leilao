# TASK 75.2.1 — FECHAMENTO FINAL DE CRUD/UI E VALIDAÇÃO

**Objetivo:** encerrar os últimos GAPs funcionais identificados na auditoria da Task 75.2, sem ampliar arquitetura, sem criar nova engine e sem alterar o histórico do imóvel real 633.

## Contexto

A Task 75.2 entregou a padronização geral de CRUD, edição e histórico. A auditoria final identificou apenas lacunas pontuais de fechamento:

1. Leiloeiro: backend já possui CRUD, mas falta ação de exclusão na UI.
2. Portal: backend já possui CRUD, mas falta ação de exclusão na UI.
3. Documento do leiloeiro: possui criação e exclusão, mas falta edição no backend e na UI.
4. Fontes do imóvel: possuem criação/listagem, mas faltam edição, exclusão e histórico.
5. Os novos fluxos precisam de cobertura automatizada e validação final do stack.

Esta task **não deve refazer o que já está entregue**. Deve completar somente esses GAPs.

---

## 1. Leiloeiros

### Backend
- Manter os endpoints existentes de criação, consulta, edição e exclusão.
- Não alterar o modelo de histórico/eventos já implementado.
- Exclusão deve preservar a rastreabilidade global conforme o padrão da Task 75.2.

### Frontend
Adicionar ação de exclusão na tela de Leiloeiros.
- Exibir confirmação antes de excluir.
- Após exclusão, atualizar a lista sem refresh manual.
- Tratar erro da API de forma visível.
- Não exibir nem registrar credenciais no fluxo.

### Critérios
- CREATE → GET → PATCH → GET → DELETE.
- Histórico/evento da exclusão preservado.
- UI permite editar e excluir.
- Nenhum segredo aparece na UI, resposta comum, histórico ou log.

---

## 2. Portais

### Backend
- Reutilizar os endpoints existentes.
- Não alterar a política de segurança da Task 75.1.
- DELETE deve gerar histórico/evento sem expor secret.

### Frontend
Adicionar ação de exclusão do portal.
- Confirmação obrigatória.
- Atualizar a lista após sucesso.
- Exibir erro de forma clara.
- Manter o fluxo de edição e recuperação protegida da credencial.

### Critérios
- CREATE → GET → PATCH → GET → DELETE.
- Histórico/evento preservado.
- secret nunca aparece em histórico/evento/listagem/log.
- Recuperação continua exigindo X-Portal-Admin-Token.

---

## 3. Documentos do leiloeiro

### Backend
Implementar edição dos metadados do documento.

Regras:
- O conteúdo/versionamento documental não pode ser sobrescrito.
- A edição altera somente metadados permitidos.
- Registrar before/after + evento.
- DELETE continua permitido para o documento cadastral do leiloeiro, conforme padrão 75.2.
- Não apagar histórico/eventos.

### Frontend
Na tela de Leiloeiros:
- Adicionar edição dos metadados do documento.
- Adicionar exclusão do documento com confirmação.
- Atualizar a lista após CREATE/PATCH/DELETE.
- Exibir erros de API.

### Critérios
- CREATE → GET → PATCH → GET → HISTORY → DELETE.
- Histórico contém before/after dos metadados.
- Conteúdo/versionamento não é sobrescrito.
- UI permite editar e excluir.

---

## 4. Fontes do imóvel

Hoje o domínio possui criação/listagem de fontes, mas ainda não está fechado no padrão CRUD/histórico.

### Backend
Implementar:
- PATCH da fonte.
- DELETE da fonte.
- histórico da fonte.
- evento correspondente às alterações/exclusão.

Regras:
- Preservar created_at e identificação original.
- PATCH altera somente campos cadastrais permitidos.
- DELETE não deve apagar histórico/eventos.
- Não criar nova análise do imóvel.
- Não alterar análises, Verdict, Risk ou Checklist existentes.

### Frontend
Na área de Fontes:
- editar fonte;
- excluir fonte com confirmação;
- atualizar lista após operação;
- exibir histórico quando o padrão da seção permitir;
- tratar erros da API.

### Critérios
- CREATE → GET → PATCH → GET → HISTORY → DELETE.
- Histórico before/after.
- Evento de alteração/exclusão.
- Nenhuma nova análise.
- Imóvel 633 permanece sem alteração analítica.

---

## 5. Testes obrigatórios

Adicionar ou ajustar testes backend e frontend cobrindo os novos fluxos.

### Backend
Cobrir no mínimo:
- delete de leiloeiro;
- delete de portal;
- patch de documento do leiloeiro;
- delete de documento do leiloeiro;
- histórico/eventos de documento;
- patch de fonte;
- delete de fonte;
- histórico/eventos de fonte;
- ausência de secret em qualquer histórico/evento/resposta comum;
- garantia de que CRUD cadastral não cria nova análise.

### Frontend
Cobrir no mínimo:
- ação de excluir leiloeiro;
- ação de excluir portal;
- edição de documento;
- exclusão de documento;
- edição de fonte;
- exclusão de fonte;
- atualização da lista após sucesso;
- tratamento de erro.

Não remover testes existentes.

---

## 6. Preservação obrigatória do imóvel 633

A propriedade **633 — COND PARQUE ARVOREDO RESIDENCIAL CLUBE** é o caso real de regressão do projeto.

Durante a task:

- NÃO executar nova análise.
- NÃO criar V10.
- NÃO chamar LLM para análise.
- NÃO executar DataJud real.
- NÃO alterar Verdict histórico.
- NÃO alterar Risk histórico.
- NÃO alterar Checklist histórico.
- Preservar exatamente as análises V1–V9 existentes.
- Preservar financial_analyses V1–V9.
- Preservar verdicts V1–V9.
- Preservar checklist_executions correspondentes.
- CRUD cadastral não pode gerar nova versão analítica.

Se for necessário validar a API, usar dados de teste isolados ou fixtures/transações apropriadas.

---

## 7. Fora de escopo — NÃO implementar

Esta task é exclusivamente de fechamento.

**Não criar:**
- novo microserviço;
- AWS;
- Redis;
- S3/MinIO;
- novo banco;
- novo vector DB;
- LLM/RAG/agente;
- scraping;
- integração real nova com DataJud;
- nova engine financeira;
- nova engine de risco;
- nova engine de Verdict;
- refatoração arquitetural ampla;
- nova tela estrutural sem necessidade;
- Task 76.

Não alterar regras de negócio já consolidadas.

---

## 8. Validação final

Executar e registrar:

### Backend
- pytest
- quantidade total de testes passed/skipped/failures.

### Frontend
- tsc --noEmit
- vitest run
- quantidade total de testes passed/failed.

### Docker
- docker compose build backend frontend
- docker compose up -d
- healthcheck do backend;
- frontend HTTP 200;
- migration head atual.

### Imóvel 633
Confirmar explicitamente:
- análises = 9;
- financial analyses = 9;
- verdicts = 9;
- versões V1–V9;
- zero V10;
- nenhuma nova análise criada pela task.

### E2E de navegador
Se Playwright/Cypress não estiver disponível, **não simular**.
Registrar explicitamente a limitação de ambiente e manter validação HTTP/jsdom/unitária como evidência complementar.

---

## 9. Documentação e commit

Ao concluir:

1. Atualizar PROJECT-STATUS.md.
2. Atualizar PROJECT-HISTORY.md.
3. Atualizar IMPLEMENTATION-REFERENCE.md.
4. Atualizar EVOLUTION-BACKLOG.md somente se algum GAP deixar de ser evolução e passar a ser entregue.
5. Registrar os arquivos alterados.
6. Criar commit com mensagem:

feat(task-75.2.1): fechar gaps finais de crud e ui

7. Informar SHA do commit.
8. Informar testes executados e resultados.
9. Informar explicitamente que o imóvel 633 permaneceu V1–V9, sem V10.

---

## 10. Definition of Done

A Task 75.2.1 só está concluída quando:

- [ ] Leiloeiro pode ser criado/editado/excluído pela UI.
- [ ] Portal pode ser criado/editado/excluído pela UI.
- [ ] Documento do leiloeiro pode ser criado/editado/excluído.
- [ ] Fonte do imóvel pode ser criada/editada/excluída.
- [ ] Todos os novos CRUDs possuem histórico/evento conforme o padrão.
- [ ] Segredo de portal nunca é exposto em histórico/evento/listagem/log.
- [ ] CRUD cadastral não cria nova análise.
- [ ] Backend passa sem falhas.
- [ ] Frontend passa TypeScript e Vitest.
- [ ] Docker/health/migration validados.
- [ ] Imóvel 633 permanece exatamente V1–V9.
- [ ] Nenhum escopo novo foi introduzido.
- [ ] Documentação atualizada.
- [ ] Commit criado e SHA informado.

**Resultado esperado:** após esta task, os GAPs funcionais identificados na auditoria 75.2 ficam fechados e o projeto entra em etapa de auditoria final/encerramento do MVP.
