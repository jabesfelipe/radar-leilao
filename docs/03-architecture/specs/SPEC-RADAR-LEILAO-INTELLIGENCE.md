# SPEC — Radar Leilão Intelligence

- **Status:** proposta para MVP
- **Versão:** 0.1.0
- **Data:** 2026-11-13
- **Repositório:** jabesfelipe/radar-leilao
- **Escopo:** módulo auxiliar e independente; não altera o core do Radar Leilão
- **Decisão inicial:** documentar e validar a coleta antes de implementar qualquer automação sobre WhatsApp

## 1. Visão

O Radar Leilão Intelligence é uma camada de inteligência externa ao produto principal. Seu objetivo é transformar discussões de comunidades, notícias, decisões judiciais e outras fontes autorizadas em conhecimento organizado e oportunidades candidatas de evolução do Radar Leilão.

O primeiro caso de uso é acompanhar um grupo de WhatsApp sobre leilões sem exigir que o usuário leia continuamente as conversas ou faça exportações manuais recorrentes.

O sistema deve:
1. receber conteúdo de fontes autorizadas;
2. normalizar e agrupar mensagens relacionadas;
3. identificar temas, fatos alegados, opiniões, dúvidas e evidências;
4. classificar relevância para leilões extrajudiciais;
5. comparar os achados com funcionalidades, specs e issues existentes no Radar Leilão;
6. produzir conhecimento, oportunidades e sugestões de backlog rastreáveis;
7. notificar somente quando houver algo que mereça atenção.

Não é objetivo transformar automaticamente conversas em regras jurídicas, alterar o checklist, modificar código ou abrir issues sem controle de duplicidade e revisão humana.

## 2. Problema e exemplo de negócio

Discussão observada no grupo:

> “Essas decisões de anulação do leilão pela falta de notificação presencial das datas do leilão aos devedores estão mais frequentes.”

> “Para esses juízes tem que intimar pessoalmente, por edital e jornal para não deixar brechas...”

Possível insight:
- tema: intimação dos devedores sobre as datas do leilão;
- domínio: jurídico / leilão extrajudicial;
- risco potencial: questionamento ou anulação do procedimento;
- pergunta para o produto: o Radar verifica a existência e a evidência dos diferentes meios de intimação aplicáveis ao caso?

A IA deve registrar isso como hipótese a investigar, não como conclusão jurídica ou requisito universal. A exigência depende da modalidade, legislação aplicável, fatos, entendimento judicial e documentação do caso. A validação deve ser feita por fonte jurídica confiável e, quando necessário, revisão profissional.

## 3. Princípios e restrições

1. **Isolamento:** o Intelligence não faz parte do runtime do Radar Leilão e não altera seu banco, APIs, workflow ou checklist no MVP.
2. **Human-in-the-loop:** nenhuma sugestão vira regra de negócio, funcionalidade implementada ou issue definitiva sem aprovação.
3. **Rastreabilidade:** todo insight deve apontar para as mensagens/fontes que o originaram, com data e contexto disponível.
4. **Deduplicação:** consolidar conversas repetidas sobre o mesmo assunto.
5. **Separação epistemológica:** distinguir fato documentado, alegação de participante, opinião, hipótese da IA e conclusão validada.
6. **Privacidade por padrão:** coletar somente o conteúdo necessário; evitar armazenar telefone, foto, perfil e outros dados pessoais dos participantes.
7. **Segurança:** não armazenar sessão, QR code, cookies ou credenciais do WhatsApp no repositório ou logs.
8. **Sem automação de escrita no WhatsApp:** o sistema não enviará mensagens nem interagirá com participantes.
9. **Sem scraping não autorizado:** automação de interface, extração de DOM ou uso de cliente não oficial não será habilitada em produção sem validação expressa de conformidade com os termos e políticas aplicáveis.
10. **Português brasileiro:** interface, relatórios e artefatos gerados em pt-BR.

## 4. Estratégia de coleta — decisão em aberto

### 4.1 Contexto do usuário

- Uso predominante: WhatsApp no iPhone.
- Necessidade: coleta recorrente sem exportação manual de conversas.
- Desejo: avaliar RPA para reduzir intervenção humana.

### 4.2 Limitações conhecidas

A API padrão do WhatsApp Business/Cloud não deve ser tratada como uma API para ingressar em um grupo comum já existente e ler seu histórico. A Groups API da Meta possui elegibilidade e limitações próprias e não é uma solução genérica para capturar comunidades existentes.

No iOS, Atalhos/Shortcuts não oferece uma interface geral e suportada para ler o histórico ou o conteúdo de mensagens de grupos do WhatsApp em segundo plano.

RPA sobre WhatsApp Web/Desktop pode ser tecnicamente prototipado, mas é frágil (mudanças de interface, sessão, paginação, mensagens editadas, mídia e sincronização) e pode caracterizar acesso automatizado ou scraping não autorizado. Os termos e a central de ajuda do WhatsApp alertam para restrições a coleta automatizada não autorizada e possível suspensão de contas. Portanto, **não aprovar scraping/RPA de sessão ou DOM como arquitetura de produção neste momento**.

### 4.3 Alternativas a avaliar

| Alternativa | Automação | Limitações | Diretriz |
|---|---|---|---|
| API oficial / Groups API | Alta, quando elegível | Não é acesso geral a grupos existentes; requisitos e limites próprios | Investigar elegibilidade, sem assumir viabilidade |
| RPA em WhatsApp Web/Desktop | Potencialmente alta | Risco de termos/conta, fragilidade técnica, privacidade | Apenas spike técnico isolado, bloqueado para produção até revisão |
| Atalho de compartilhamento/encaminhamento para captura | Parcial | Exige ação pontual do usuário, mas não exportação do histórico | Alternativa de contingência simples |
| Canal/grupo próprio com fonte consentida | Alta, conforme integração suportada | Exige adesão dos participantes e mudança de hábito | Alternativa futura |
| Fontes públicas e feeds jurídicos | Alta | Não substitui conversas privadas do grupo | Complemento futuro |

### 4.4 Spike obrigatório de coleta

Antes de escolher um coletor, produzir uma avaliação curta contendo:
- viabilidade real no iPhone e/ou desktop;
- quais dados seriam acessados e armazenados;
- compatibilidade com termos/políticas do WhatsApp;
- consentimento e expectativas dos participantes;
- risco de bloqueio da conta;
- robustez, custo operacional e manutenção;
- tratamento de mensagens apagadas/editadas e mídias;
- alternativa de desligamento imediato.

**Critério de decisão:** se a única forma de coleta contínua depender de scraping não autorizado, não implementar esse caminho. Manter o pipeline de inteligência independente do adaptador de origem e utilizar fonte alternativa autorizada.

## 5. Escopo funcional do MVP

### MVP-01 — Ingestão e normalização
- receber mensagens por um adaptador de entrada aprovado;
- aceitar lote de texto estruturado para testes e validação do pipeline;
- registrar origem, identificador externo quando disponível, data/hora e texto;
- normalizar quebras, citações, links e metadados;
- detectar duplicidade por identificador e hash normalizado;
- preservar vínculo entre mensagens de uma mesma conversa;
- permitir reprocessamento idempotente.

O suporte a arquivo de importação pode existir para testes e contingência, mas não deve ser o fluxo operacional desejado pelo usuário.

### MVP-02 — Análise e extração de conhecimento
- classificar mensagens por tema;
- agrupar mensagens semanticamente relacionadas;
- identificar entidades relevantes: modalidade, tribunal, juiz/órgão quando explicitamente citado, cartório, leiloeiro, documento, prazo e tipo de risco;
- distinguir afirmação, opinião, pergunta, experiência pessoal e referência documental;
- gerar resumo com evidências e incertezas;
- classificar relevância e confiança separadamente;
- identificar assuntos recorrentes em janelas de tempo;
- não inferir dados ausentes.

Categorias iniciais:
- jurídico e jurisprudência;
- intimação e notificação;
- edital e publicidade;
- matrícula e registro;
- ocupação e desocupação;
- débitos, tributos e condomínio;
- avaliação e preço;
- leiloeiro e plataforma;
- financiamento e pagamento;
- fraude, nulidade e riscos procedimentais;
- oportunidades e estratégias.

### MVP-03 — Cruzamento com o Radar Leilão
O Intelligence deve consultar documentação versionada e, quando disponível, issues abertas/fechadas do repositório para responder:
- já existe funcionalidade ou regra relacionada?
- existe SPEC ou documentação relacionada?
- há issue aberta ou encerrada sobre o tema?
- o achado complementa, contradiz ou questiona algo existente?
- qual módulo pode ser impactado?

O cruzamento inicial pode usar arquivos Markdown do repositório e busca de issues do GitHub. Não precisa acessar o banco ou APIs de produção do Radar Leilão.

### MVP-04 — Oportunidades e saídas
Tipos de resultado:
- **CONHECIMENTO:** informação útil para a base de conhecimento, sem mudança de produto sugerida;
- **MELHORIA:** possível aprimoramento de funcionalidade existente;
- **NOVA OPORTUNIDADE:** possível capacidade nova;
- **ALERTA:** tema relevante que exige atenção, investigação ou validação rápida;
- **DESCARTADO:** irrelevante, duplicado ou sem evidência suficiente.

Para cada oportunidade:
- título e resumo;
- categoria e subcategoria;
- problema observado;
- impacto potencial;
- evidências/fontes;
- data da primeira e última ocorrência;
- recorrência observada;
- relevância (0–100);
- confiança da extração (baixa/média/alta);
- validação jurídica (não avaliada / pendente / validada / refutada);
- módulos e documentos relacionados;
- sugestão de próximo passo;
- estado de revisão humana.

Gerar:
- documento Markdown de conhecimento;
- proposta de melhoria/spec quando fizer sentido;
- rascunho de issue GitHub, sem publicação automática no primeiro MVP;
- resumo periódico.

### MVP-05 — Notificações e digest
- digest semanal com volume processado, principais temas e oportunidades;
- alerta extraordinário somente para achados de alta relevância e confiança;
- evitar notificação por cada mensagem;
- permitir marcar oportunidade como revisada, aprovada, descartada ou em investigação.

## 6. Score de priorização

Score inicial, configurável e explicável:

| Dimensão | Peso |
|---|---:|
| Relevância para leilões extrajudiciais | 30% |
| Impacto jurídico/financeiro potencial | 30% |
| Recorrência independente do assunto | 20% |
| Potencial de melhoria do Radar Leilão | 20% |

O score não representa probabilidade jurídica de êxito ou nulidade. Exibir também a confiança da extração e a qualidade das fontes, sem misturar esses conceitos com a pontuação de prioridade.

## 7. Arquitetura lógica proposta

~~~mermaid
flowchart TD
    A[Fontes autorizadas] --> B[Adaptadores de ingestão]
    B --> C[Inbox / mensagens brutas]
    C --> D[Normalização e deduplicação]
    D --> E[Classificação e agrupamento IA]
    E --> F[Extração de conhecimento]
    F --> G[Cruzamento com docs e issues do Radar]
    G --> H[Oportunidades candidatas]
    H --> I[Revisão humana]
    I --> J[Conhecimento Markdown]
    I --> K[Rascunho de issue / SPEC]
    I --> L[Digest e notificações]
~~~

### Componentes lógicos

| Componente | Responsabilidade |
|---|---|
| Source Adapter | Contrato comum para receber conteúdo de diferentes fontes |
| Ingestion Service | Validar, persistir e deduplicar mensagens |
| Normalizer | Padronizar conteúdo e metadados |
| Topic Classifier | Categorizar e identificar assuntos |
| Conversation Grouper | Agrupar mensagens relacionadas |
| Knowledge Extractor | Extrair afirmações, evidências, entidades e incertezas |
| Radar Context Provider | Consultar documentação e issues do projeto |
| Opportunity Engine | Comparar achados e propor oportunidades |
| Review Workflow | Controlar aprovação humana |
| Artifact Generator | Gerar Markdown, SPECs e rascunhos de issues |
| Digest Notifier | Produzir resumos e alertas |

### Stack de referência

A stack deve permanecer enxuta e compatível com o ecossistema já utilizado no projeto:
- Python e FastAPI para serviços;
- PostgreSQL para persistência;
- pgvector somente se a busca semântica demonstrar valor no MVP;
- LLM via gateway/provider configurável;
- GitHub API para leitura de documentação/issues e, após aprovação, criação de issues;
- Docker Compose para execução local.

Não introduzir microserviços, AWS, Knowledge Graph ou LangGraph como requisito do MVP. Reutilizar componentes existentes somente quando isso não acoplar o módulo ao core. A arquitetura final deve ser validada na implementação, não presumida nesta SPEC.

## 8. Modelo conceitual inicial

### Source
- id
- type
- name
- status
- collection_policy
- created_at

### RawMessage
- id
- source_id
- external_id (nullable)
- occurred_at (nullable)
- author_reference (pseudonimizada ou omitida)
- content
- content_hash
- reply_to_external_id (nullable)
- metadata_minimized
- ingested_at

### Topic
- id
- name
- category
- description

### Insight
- id
- title
- summary
- insight_type
- relevance_score
- extraction_confidence
- legal_validation_status
- first_seen_at
- last_seen_at
- review_status

### InsightEvidence
- id
- insight_id
- raw_message_id
- evidence_excerpt
- evidence_type
- source_reference

### ProductOpportunity
- id
- insight_id
- title
- description
- impact
- suggested_action
- related_paths
- github_issue_number (nullable)
- status

Este modelo é conceitual. Não criar migrations no banco principal do Radar Leilão. Persistência e schema próprios do módulo serão definidos na etapa de implementação.

## 9. Fluxo de revisão humana

Estados sugeridos:
- NOVO
- EM_ANALISE
- VALIDACAO_EXTERNA
- APROVADO
- DESCARTADO
- CONVERTIDO_EM_BACKLOG

Aprovação deve exigir:
- evidência rastreável;
- ausência de duplicidade conhecida;
- justificativa de relevância;
- classificação explícita do que ainda é hipótese;
- validação jurídica externa quando a oportunidade envolver interpretação normativa ou jurisprudencial.

Somente após aprovação o usuário poderá solicitar criação de issue no GitHub. Não criar issue, branch, commit, PR ou alteração de código automaticamente no MVP.

## 10. Privacidade, segurança e governança

- Avaliar base legal, transparência e necessidade de consentimento para o tratamento do conteúdo do grupo, considerando LGPD e expectativas dos participantes.
- Não coletar lista de participantes, telefones, fotos de perfil ou status.
- Pseudonimizar autores quando a identificação não for necessária para compreender o contexto.
- Não enviar dados pessoais ou conteúdo integral desnecessário ao provedor de IA.
- Definir retenção e exclusão de mensagens brutas.
- Proteger tokens do GitHub e chaves de IA por variáveis de ambiente/secret store; nunca commitar segredos.
- Restringir acesso ao conteúdo bruto.
- Registrar auditoria de ingestão, processamento, revisão e publicação.
- Não usar conteúdo do grupo para treinamento de modelos.
- Prever exclusão de fonte e de seus dados derivados quando solicitado e aplicável.

## 11. Requisitos não funcionais

- **Idempotência:** reprocessar lote sem duplicar mensagens ou insights.
- **Observabilidade:** logs estruturados sem conteúdo pessoal desnecessário.
- **Resiliência:** falha do provedor de IA não pode perder mensagens ingeridas.
- **Custo:** agrupar mensagens, filtrar ruído e evitar chamadas LLM por mensagem.
- **Explicabilidade:** toda sugestão deve mostrar por que foi criada e quais evidências a sustentam.
- **Portabilidade:** adaptadores de fonte independentes do pipeline de análise.
- **Segurança:** credenciais fora do Git e acesso mínimo necessário.

## 12. Critérios de aceite do MVP

1. Dado um lote de mensagens de teste, o sistema persiste e deduplica sem perda de vínculo com a origem.
2. Mensagens relacionadas são agrupadas em um único assunto quando apropriado.
3. O sistema classifica o assunto e separa alegações, opiniões, perguntas e evidências.
4. O exemplo de intimação gera hipótese de oportunidade, sem afirmar que existe obrigação universal de intimação por todos os meios.
5. Cada insight permite consultar as mensagens que o sustentam.
6. O sistema consulta documentação e issues do Radar Leilão antes de sugerir backlog.
7. Oportunidades duplicadas são sinalizadas e consolidadas.
8. O score e a confiança são exibidos separadamente.
9. O sistema gera relatório Markdown e digest semanal.
10. Nenhuma issue ou alteração no core é publicada sem aprovação explícita.
11. O pipeline de análise funciona independentemente do adaptador WhatsApp.
12. A estratégia de coleta tem decisão formal de conformidade antes de qualquer execução contínua.

## 13. Plano de entrega

| Fase | Entrega | Fora do escopo |
|---|---|---|
| P0 — Discovery | Spike de coleta, riscos, privacidade e decisão de fonte | Automação de scraping em produção |
| P1 — Foundation | Projeto isolado, schema próprio, ingestão de lote e deduplicação | Integração com core |
| P2 — Intelligence | Classificação, agrupamento, extração e evidências | Regras jurídicas automáticas |
| P3 — Radar Context | Leitura de docs/issues e detecção de duplicidade | Escrita automática no GitHub |
| P4 — Outputs | Markdown, digest e revisão humana | Alteração automática de código/checklist |
| P5 — Conectores | Fonte contínua aprovada e outras fontes públicas | Coleta de fontes sem autorização |

## 14. Fora de escopo do MVP

- Alterar checklist, workflow, motor jurídico ou banco de dados do Radar Leilão.
- Fazer parecer jurídico ou declarar nulidade de leilão.
- Atualizar automaticamente regras com base em conversa de grupo.
- Fazer scraping de WhatsApp Web ou extrair DOM em produção sem autorização e validação de conformidade.
- Enviar mensagens, responder participantes ou administrar grupos.
- Processar todos os tipos de mídia/áudio no primeiro ciclo.
- Criar painel completo antes de validar o valor do pipeline.

## 15. Decisões pendentes

- [ ] Confirmar fonte de coleta tecnicamente viável e compatível com as regras aplicáveis.
- [ ] Definir se a primeira execução será local ou em ambiente dedicado.
- [ ] Definir política de retenção das mensagens brutas.
- [ ] Definir canal de notificação (digest/documento inicialmente).
- [ ] Definir provedor/modelo de IA e limites de custo.
- [ ] Definir formato de revisão e aprovação de oportunidades.

## 16. Referências

- WhatsApp — Termos de Serviço: https://www.whatsapp.com/legal/terms-of-service
- WhatsApp Help Center — coleta automatizada de informações pessoais: https://faq.whatsapp.com/434518851968943
- WhatsApp Business — Política de Negócios e proteção de dados: https://business.whatsapp.com/policy/preview?lang=pt_BR
- Meta Developers — consultar a documentação da Groups API na etapa P0 para confirmar elegibilidade e limitações vigentes.
- Radar Leilão — documentação de produto: docs/02-product/
- Radar Leilão — arquitetura e integrações: docs/03-architecture/

---

**Diretriz final:** primeiro provar que conseguimos transformar conversas em conhecimento confiável e oportunidades úteis. A coleta contínua do WhatsApp é uma dependência a ser resolvida com segurança; não deve comprometer a conta do usuário nem a privacidade dos participantes.
