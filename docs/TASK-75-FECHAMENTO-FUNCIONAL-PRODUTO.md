# TASK 75 — FECHAMENTO FUNCIONAL DO PRODUTO RADAR LEILÃO

**Data:** 01/10/2026  
**Status:** 🟡 PENDENTE — próxima task operacional do Kiro  
**Natureza:** fechamento funcional / UX / produto / hardening  
**Prioridade:** P0 para fechamento do MVP atual

## 1. Objetivo

Transformar o Radar Leilão de uma aplicação com módulos parcialmente expostos em um produto navegável de ponta a ponta, sem criar nova arquitetura e sem reabrir os motores de negócio já implementados.

O Radar já possui cadastro de imóveis/leilões, documentos/evidências, matrícula, edital, Jurídico/Judicial API, Finance Engine, Mercado, Ocupação, Checklist, Risk Engine, Verdict Engine, Histórico, RAG/embeddings, agentes LLM e reanálise incremental.

A validação manual atual mostrou que Dashboard e Imóveis funcionam, mas vários menus laterais ainda são vazios/placeholders. Financeiro global, Mercado, Ocupação, Checklist, Riscos, Veredito e Histórico precisam ser transformados em centrais úteis reutilizando as seções que já existem no Dossiê.

Também precisamos de cadastro de Leiloeiro, portais/acessos, credenciais protegidas e documentos do leiloeiro.

---

## 2. FASE 0 — AUDITORIA OBRIGATÓRIA

Antes de codificar:

1. levantar todos os menus da sidebar;
2. mapear cada menu para o componente/rota/API atual;
3. classificar como funcional, parcial, placeholder ou duplicado;
4. mapear APIs/modelos/migrations existentes;
5. localizar a origem dos registros de demonstração;
6. identificar registros como "Imóvel Fin";
7. confirmar o estado atual do imóvel 633;
8. garantir que V1–V9 do imóvel 633 não serão alteradas.

Entregar um mapa:

| Menu | Estado | Componente/API existente | Ação |
|---|---|---|---|
| Dashboard | funcional | existente | evoluir |
| Imóveis | funcional | existente | evoluir |
| Documentos | parcial/global | existente | centralizar |
| Jurídico | parcial/global | existente | centralizar |
| Financeiro | placeholder global | FinancialSection/API | centralizar |
| Mercado | placeholder/parcial | MarketSection/API | centralizar |
| Ocupação | placeholder/parcial | OccupancySection/API | centralizar |
| Checklist | placeholder/parcial | ChecklistSection/API | centralizar |
| Riscos | placeholder/parcial | RiskSection/API | centralizar |
| Veredito | placeholder/parcial | VerdictSection/API | centralizar |
| Histórico | placeholder/parcial | HistorySection/API | centralizar |
| Leiloeiros | inexistente | novo domínio | implementar |

---

## 3. REGRA FUNDAMENTAL

Reutilizar os componentes, APIs e motores existentes.

Localizar e reutilizar, quando aplicável:

- FinancialSection;
- MarketSection;
- OccupancySection;
- ChecklistSection;
- RiskSection;
- VerdictSection;
- HistorySection;
- ProcessSection;
- DocumentsSection;
- RegistrationSection;
- AuctionNoticeSection;
- Finance Engine;
- Market Engine;
- Occupancy domain;
- Checklist Engine;
- Risk Engine;
- Verdict Engine;
- Historical/Event services;
- Judicial API;
- Document/RAG infrastructure.

Não criar motores paralelos.

---

## 4. IDENTIDADE VISUAL

Substituir a aparência atual navy + dourado por uma identidade mais marcante e moderna.

Direção:

- grafite;
- azul petróleo;
- branco/cinza claro;
- laranja/cobre como destaque;
- verde para positivo;
- amarelo para atenção;
- vermelho para risco.

Tokens sugeridos:

- BACKGROUND #F4F6F8
- SIDEBAR #101820
- PRIMARY #0F4C5C
- ACCENT #E07A2D
- SUCCESS #16855B
- WARNING #D99A22
- DANGER #C94A4A

Os valores são referência visual, não contrato.

Regras:

- não usar laranja em tudo;
- accent para CTA, oportunidade e indicadores importantes;
- contraste acessível;
- reutilizar o design system existente;
- não trocar toda a biblioteca de UI sem necessidade.

Objetivo: o Radar deve parecer produto de inteligência/decisão imobiliária, não CRUD administrativo.

---

## 5. SIDEBAR

Revisar:

1. Dashboard
2. Imóveis
3. Documentos
4. Jurídico
5. Financeiro
6. Mercado
7. Ocupação
8. Checklist
9. Riscos
10. Veredito
11. Histórico
12. Leiloeiros

Nenhum menu pode continuar como placeholder.

Se a funcionalidade pertence ao Dossiê, o hub global deve resumir e levar ao imóvel correspondente.

---

## 6. DASHBOARD

Transformar em painel de decisão.

Indicadores calculados dos dados reais:

- imóveis no Radar;
- imóveis em análise;
- imóveis com pendências;
- riscos altos;
- oportunidades;
- análises recentes.

Pipeline, usando somente estados existentes:

Cadastrado → Documentação → Análise → Diligência → Pronto para decisão.

Alertas:

- riscos;
- documentação pendente;
- preço máximo provisório;
- análise desatualizada;
- pendências jurídicas;
- pendências financeiras.

Cada alerta deve levar ao imóvel/módulo correspondente.

Não inventar números.

---

## 7. IMÓVEIS

Melhorar a listagem com, quando disponível:

- imóvel;
- cidade/UF;
- origem;
- leilão;
- avaliação;
- lance;
- preço máximo;
- TCO;
- ROI;
- risco;
- ocupação;
- pendências;
- veredito.

### Dados de teste

Investigar a origem dos registros artificiais.

Não apagar automaticamente.

Separar dados reais de fixtures/demonstração.

Antes de excluir qualquer coisa:

- identificar origem;
- comprovar que é teste;
- preservar imóvel 633;
- preservar histórico;
- preservar documentos;
- preservar V1–V9.

---

## 8. CENTRAL DE DOCUMENTOS

Criar visão global reutilizando o módulo documental existente.

Mostrar:

- total;
- tipo;
- imóvel;
- versão;
- data;
- origem;
- status;
- evidências.

Filtros:

- Todos;
- Edital;
- Matrícula;
- Jurídico;
- Financeiro;
- Outros.

Clique deve levar ao documento/dossiê correspondente.

Não duplicar o pipeline documental.

---

## 9. CENTRAL JURÍDICA

Reutilizar Judicial API e componentes existentes.

Mostrar:

- processos encontrados;
- processos vinculados;
- riscos;
- pendências;
- última consulta.

Tabela:

Imóvel | Processo | Tribunal | Correlação | Nível | Risco | Status

Manter as regras atuais de correlação.

Não alterar fórmula financeira.

Não transformar correlação automática em confirmação automática de identidade.

Não inventar processos.

---

## 10. CENTRAL FINANCEIRA — PRIORIDADE ALTA

O Finance Engine atual já cobre:

- aquisição;
- comissão;
- ITBI;
- registro;
- débitos;
- condomínio;
- IPTU;
- custos jurídicos;
- desocupação;
- reforma;
- carregamento;
- outros;
- valor de mercado;
- aluguel;
- custo total;
- desconto;
- margem;
- resultado líquido;
- ROI;
- yield;
- preço máximo;
- cenários;
- custos desconhecidos;
- resultado provisório/definitivo.

Não recriar fórmulas.

A tarefa é expor corretamente essas capacidades na UI.

### 10.1 TCO

Mostrar:

Lance + Comissão + ITBI + Registro + Condomínio + IPTU + Débitos + Reforma + Desocupação + Jurídico + Carregamento + Outros = TCO.

Cada custo deve ter status:

- INFORMADO;
- ESTIMADO;
- DESCONHECIDO;
- NÃO APLICÁVEL.

Desconhecido nunca deve virar zero silenciosamente.

### 10.2 Preço máximo

Exibir valor e estado:

DEFINITIVO ou PROVISÓRIO.

Quando provisório, mostrar exatamente os custos desconhecidos.

O usuário precisa entender que o teto provisório pode estar superestimado.

### 10.3 Break-even

Adicionar como indicador explícito caso ainda não exista como saída do domínio.

Definição:

"preço mínimo de saída necessário para recuperar o investimento considerando os custos de venda parametrizados."

Se for necessário implementar:

- usar teste unitário;
- documentar fórmula;
- não duplicar regras existentes;
- não usar LLM.

### 10.4 Venda

Mostrar:

- valor de venda;
- corretagem;
- tributos;
- custo de saída;
- resultado líquido;
- margem líquida;
- ROI.

Separar custos de aquisição/operação de custos de saída.

### 10.5 Aluguel

Mostrar quando houver dados:

- aluguel mensal;
- yield mensal;
- yield anual;
- comparáveis;
- fonte/data.

Não inventar aluguel.

### 10.6 Cenários

Permitir configurar explicitamente:

- Conservador;
- Base;
- Otimista.

Premissas:

- valor de venda;
- reforma;
- desocupação;
- carregamento;
- prazo;
- justificativa.

Sem premissa, mostrar "CENÁRIO NÃO CONFIGURADO".

### 10.7 Margem de segurança

Mostrar:

Valor de mercado - TCO = Margem

e Margem %.

### 10.8 Pendências financeiras

Mostrar claramente:

- ITBI;
- registro;
- comissão;
- corretagem;
- tributo;
- condomínio;
- IPTU;
- débitos;
- reforma;
- desocupação;
- outros custos relevantes.

Distinguir INFORMADO / ESTIMADO / DESCONHECIDO / NÃO APLICÁVEL.

---

## 11. CHECKLIST FINANCEIRO MÍNIMO

Garantir que a UI consiga representar:

- lance/preço de aquisição;
- comissão do leiloeiro;
- ITBI;
- registro;
- escritura quando aplicável;
- condomínio;
- IPTU;
- débitos;
- reforma;
- regularização;
- desocupação;
- custos jurídicos;
- carregamento;
- manutenção;
- corretagem de venda;
- tributação da venda;
- valor de mercado;
- valor de saída;
- prazo de venda;
- aluguel;
- yield;
- ROI;
- margem;
- preço máximo;
- break-even.

Itens que não façam parte do modelo atual devem ser documentados como evolução, não inventados.

---

## 12. CENTRAL DE MERCADO

Reutilizar Market Engine/comparáveis.

Mostrar:

- comparáveis de venda;
- comparáveis de aluguel;
- preço/m²;
- aluguel/m²;
- valor estimado;
- quantidade;
- origem;
- data;
- características.

Tabela:

Imóvel | Distância | Área | Quartos | Preço | Preço/m² | Aluguel | Fonte | Data

Não criar scraping novo.

Não inventar comparáveis.

---

## 13. CENTRAL DE OCUPAÇÃO/DESOCUPAÇÃO

Mostrar:

- status;
- tipo/perfil conhecido;
- evidências;
- custo estimado;
- risco;
- impacto financeiro.

Status compatíveis com o domínio atual:

- DESOCUPADO;
- OCUPADO;
- DESCONHECIDO;
- EM_ANALISE.

Reutilizar o fluxo:

Ocupação → Financeiro → Risk → Veredito.

Não criar novo agente LLM de desocupação.

---

## 14. CENTRAL DE CHECKLIST

Mostrar:

- total;
- confirmados;
- pendentes;
- atenção;
- riscos.

Filtros:

- Todos;
- Pendente;
- Confirmado;
- Risco/Atenção;
- Não aplicável.

Cada item deve permitir chegar a:

- imóvel;
- evidência;
- documento;
- versão;
- análise.

Não alterar os 27 canonical keys nesta task.

---

## 15. CENTRAL DE RISCOS

Mostrar:

- risco;
- imóvel;
- domínio;
- severidade;
- origem;
- evidência;
- status;
- versão.

Filtros por severidade.

Não alterar Risk Engine salvo defeito reproduzido.

---

## 16. CENTRAL DE VEREDITOS

Mostrar globalmente, quando disponível:

- imóvel;
- preço atual;
- preço máximo;
- TCO;
- ROI;
- margem;
- risco;
- ocupação;
- pendências;
- veredito;
- versão da análise.

O Veredito continua explicável.

Não alterar Verdict Engine salvo regressão objetiva.

---

## 17. CENTRAL DE HISTÓRICO

Criar timeline global com:

- data/hora;
- evento;
- imóvel;
- versão;
- origem;
- domínio;
- causa;
- evidência quando aplicável.

Não expor segredos ou credenciais.

---

## 18. NOVO DOMÍNIO — LEILOEIROS

Criar cadastro:

- nome;
- CPF/CNPJ quando aplicável;
- empresa;
- registro/identificação profissional;
- telefone;
- e-mail;
- site;
- endereço;
- observações;
- status.

Não obrigar campos que a fonte não possua.

---

## 19. PORTAIS E ACESSOS

Permitir:

- portal;
- URL;
- usuário/e-mail;
- senha;
- tipo de acesso;
- observação;
- 2FA habilitado;
- status;
- última validação.

### Segurança obrigatória

Senha:

- nunca em texto puro;
- nunca em GET de listagem;
- nunca em logs;
- nunca em histórico;
- nunca em evidência;
- nunca enviada a LLM;
- nunca enviada ao RAG;
- nunca retornada em payload comum.

Se for necessário recuperar a senha para uma ação explícita, criar endpoint separado, protegido e auditável.

Não criar AWS Secrets Manager nesta task.

---

## 20. DOCUMENTOS DO LEILOEIRO

Permitir:

- contrato;
- credenciamento;
- documentação;
- termos;
- comprovantes;
- outros.

Campos:

- tipo;
- nome;
- arquivo;
- versão;
- data;
- observação.

Reutilizar infraestrutura documental.

---

## 21. RELACIONAMENTO LEILOEIRO ↔ LEILÃO

No cadastro/edição do leilão:

Leiloeiro → Portal → Acesso.

Um leiloeiro pode possuir vários portais/acessos e vários imóveis/leilões podem apontar para o mesmo leiloeiro.

Não duplicar cadastro.

---

## 22. MODELO DE DADOS

Antes de criar migration:

- verificar entidades existentes;
- evitar duplicar Auction.auctioneer sem necessidade.

Se o campo atual for texto, migrar incrementalmente para entidade relacionada, preservando o texto histórico.

Modelo conceitual:

Auctioneer
- dados cadastrais
- PortalAccess
  - username
  - secret
  - status
- Documents

Credenciais devem ser separadas do cadastro do leiloeiro.

---

## 23. SEGURANÇA

Nunca registrar:

- senha;
- token;
- cookie;
- session ID;
- credencial;
- API key.

Nunca enviar credenciais para:

- LLM;
- RAG;
- embeddings;
- histórico;
- DomainEvent;
- evidências.

Criar testes de não exposição.

---

## 24. E2E FINANCEIRO NO NAVEGADOR

Esta task deve resolver a pendência atual de UI.

Adicionar Playwright se adequado.

Fluxo:

abrir Radar → abrir imóvel → Financeiro → informar premissas → salvar → recarregar → conferir persistência → alterar premissa → recalcular → verificar preço máximo → verificar definitivo/provisório → verificar histórico.

Validar também:

- cenários;
- pendências;
- TCO;
- venda;
- ROI;
- yield;
- margem;
- break-even, se implementado.

Não executar nova análise LLM do imóvel 633 para testar o navegador.

---

## 25. E2E DOS MENUS

Validar no navegador:

- Dashboard abre e mostra dados reais;
- Imóveis lista e abre dossiê;
- Documentos lista e filtra;
- Jurídico lista processos e navega;
- Financeiro lista e navega;
- Mercado lista comparáveis;
- Ocupação mostra status;
- Checklist filtra;
- Riscos filtra;
- Veredito navega;
- Histórico mostra timeline;
- Leiloeiros permite cadastro/edição/portal/credencial/documento/associação.

Nenhum menu pode apresentar tela de fundação vazia.

---

## 26. IMÓVEL 633

REGRA ESPECIAL:

Não alterar V1–V9.

Não:

- criar V10;
- criar análise LLM;
- alterar Checklist histórico;
- alterar Veredito histórico;
- reprocessar documentos sem necessidade;
- apagar evidências.

Para testes de criação/edição, usar fixture ou rollback.

---

## 27. TESTES BACKEND

Executar:

pytest -q

Adicionar testes para:

- leiloeiro;
- portal;
- credencial;
- segurança da credencial;
- documentos do leiloeiro;
- associação leiloeiro/leilão;
- break-even, se implementado;
- novos endpoints;
- filtros dos hubs;
- regressões.

Não criar testes artificiais.

---

## 28. TESTES FRONTEND

Executar:

vitest run

e:

tsc --noEmit

Cobrir componentes novos e fluxos críticos.

---

## 29. PLAYWRIGHT

Adicionar somente para E2E de navegador.

Registrar:

- navegador;
- URLs;
- fluxos;
- resultado;
- falhas;
- screenshots/evidências quando úteis.

---

## 30. DOCUMENTAÇÃO

Atualizar conforme necessário:

- README.md;
- docs/PROJECT-STATUS.md;
- docs/PROJECT-HISTORY.md;
- docs/IMPLEMENTATION-REFERENCE.md;
- docs/EVOLUTION-BACKLOG.md;
- docs/SPEC-VIBE-CODING-RADAR-LEILAO.md.

Não apagar nem reescrever histórico antigo.

Registrar esta task como fase de fechamento do produto após Tasks 2–5 e integração jurídica.

---

## 31. FORA DO ESCOPO

Não fazer:

- microserviços novos;
- AWS;
- Redis;
- MinIO;
- S3;
- Knowledge Graph;
- novo vector DB;
- novo RAG;
- novo agente;
- novo provider LLM;
- troca de LLM;
- scraping de novos portais;
- automação completa de portais;
- integração automática de credenciais;
- leilão judicial;
- DataJud real se estiver gated;
- backfill global de embeddings;
- reprocessamento global;
- V10 do imóvel 633;
- alteração dos 27 canonical keys;
- alteração de Verdict Engine sem defeito;
- alteração de Risk Engine sem defeito;
- refatoração ampla sem relação com esta task.

---

## 32. CRITÉRIOS DE ACEITE

### Produto
- [ ] nenhum menu principal é placeholder;
- [ ] Dashboard funcional;
- [ ] Imóveis funcional;
- [ ] Documentos funcional;
- [ ] Jurídico funcional;
- [ ] Financeiro funcional;
- [ ] Mercado funcional;
- [ ] Ocupação funcional;
- [ ] Checklist funcional;
- [ ] Riscos funcional;
- [ ] Veredito funcional;
- [ ] Histórico funcional;
- [ ] Leiloeiros funcional.

### Visual
- [ ] nova identidade visual;
- [ ] contraste adequado;
- [ ] sidebar consistente;
- [ ] estados visuais coerentes.

### Financeiro
- [ ] TCO;
- [ ] custos por status;
- [ ] preço máximo;
- [ ] definitivo/provisório;
- [ ] pendências;
- [ ] valor de saída;
- [ ] custo de saída;
- [ ] resultado líquido;
- [ ] margem;
- [ ] ROI;
- [ ] aluguel;
- [ ] yield;
- [ ] cenários;
- [ ] break-even, se incorporado ao domínio.

### Leiloeiro
- [ ] cadastro;
- [ ] edição;
- [ ] portais;
- [ ] credenciais;
- [ ] proteção da senha;
- [ ] documentos;
- [ ] associação ao leilão.

### Segurança
- [ ] senha não aparece em listagens;
- [ ] senha não aparece em logs;
- [ ] senha não aparece em histórico;
- [ ] senha não vai para LLM/RAG;
- [ ] testes de não exposição.

### E2E
- [ ] navegador validado;
- [ ] Financeiro validado;
- [ ] menus globais validados;
- [ ] Leiloeiros validado;
- [ ] persistência validada.

### Regressão
- [ ] backend verde;
- [ ] frontend verde;
- [ ] TypeScript verde;
- [ ] E2E navegador verde;
- [ ] imóvel 633 V1–V9 preservado;
- [ ] nenhuma V10;
- [ ] nenhuma alteração histórica indevida.

---

## 33. CRITÉRIO DE PARADA

Depois de cumprir os critérios:

1. atualizar documentação;
2. executar testes finais;
3. registrar resultados reais;
4. criar commit;
5. parar.

Não iniciar automaticamente outra fase.

---

## 34. ENTREGA FINAL DO KIRO

Informar:

### Arquivos alterados
Lista completa.

### Migrations
Lista completa ou "nenhuma".

### APIs novas
Lista.

### Componentes novos
Lista.

### Componentes reutilizados
Lista.

### Testes
Comandos e números reais.

### E2E
Fluxos executados e resultados.

### Segurança
Como as credenciais foram protegidas.

### Imóvel 633
Confirmar V1–V9 preservadas.

### Financeiro
Confirmar indicadores implementados e eventuais lacunas reais.

### Pendências
Somente pendências reais.

### Commit
SHA completo.

---

## 35. DEFINIÇÃO DE MVP ATUAL FECHADO

Após aprovação desta task, o MVP atual poderá ser considerado funcionalmente fechado quando o fluxo:

Cadastro → Leilão → Leiloeiro → Documentos → Jurídico → Financeiro → Mercado → Ocupação → Checklist → Riscos → Veredito → Histórico

estiver navegável e rastreável pela interface.

A partir daí, novas fontes, scraping, automações, mercado avançado, DataJud real, leilão judicial, infraestrutura externa e inteligência avançada de oportunidades devem ser Fase 2/backlog.

---

## 36. PRINCÍPIO FINAL

O objetivo não é fazer o Radar parecer maior.

É fazer o Radar parecer coerente.

Cada menu precisa existir por um motivo.

Cada número precisa vir de uma fonte.

Cada cálculo precisa vir do domínio determinístico.

Cada conclusão importante precisa possuir evidência.

Cada credencial precisa ser protegida.

Cada alteração importante precisa possuir histórico.

O usuário deve conseguir sair de um imóvel até uma decisão fundamentada sem encontrar telas vazias ou módulos de fachada.
