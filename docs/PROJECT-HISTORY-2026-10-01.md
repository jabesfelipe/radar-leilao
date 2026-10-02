# REGISTRO DE HISTÓRICO — 01/10/2026

## TASK 75 — FECHAMENTO FUNCIONAL DO PRODUTO

Foi criada a Task 75 para consolidar o fechamento funcional do Radar Leilão após a implementação dos motores técnicos e da integração jurídica.

### Motivo

A validação manual do frontend mostrou que a aplicação ainda possui menus globais sem função útil/sem conteúdo, apesar de existirem componentes funcionais dentro do Dossiê do imóvel.

Também foi identificada a necessidade de:

- nova identidade visual;
- centralização dos módulos;
- cadastro de Leiloeiros;
- cadastro de portais;
- armazenamento seguro de credenciais;
- documentos do leiloeiro;
- fechamento da experiência financeira;
- E2E real pelo navegador;
- revisão dos dados de demonstração;
- consolidação da documentação.

### Estado financeiro

As Tasks 2–5 já implementaram e validaram por HTTP o núcleo determinístico do financeiro, incluindo preço máximo, cenários, resultado de venda, ROI, margem, custos desconhecidos e estado definitivo/provisório.

A Task 75 não deve recriar o Finance Engine. Ela deve expor essas capacidades de forma completa na UI e validar o fluxo no navegador.

### Estado jurídico

A integração Judicial API → correlação → sinal → Checklist/Risk/Verdict já está implementada.

A Task 75 também não deve recriar o módulo jurídico; deve transformá-lo em uma central global reutilizando os componentes existentes.

### Segurança

O cadastro de Leiloeiros introduz credenciais de portais. Senhas não podem ser armazenadas em texto puro, retornadas em listagens, registradas em logs ou enviadas para LLM/RAG/histórico/evidências.

### Imóvel 633

V1–V9 devem permanecer intactas.

A Task 75 não deve executar V10.

### Decisão

A Task 75 passa a ser o próximo marco operacional para fechamento do MVP atual.

Depois da aprovação da Task 75, novas funcionalidades devem ser classificadas como Fase 2/backlog, salvo correção crítica.
