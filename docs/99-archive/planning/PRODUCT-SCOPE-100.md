# RADAR LEILÃO — PRODUCT SCOPE 100%

**Versão:** 1.0  
**Data:** 07/11/2026  
**Documento complementar:** `ROADMAP-MASTER.md`

## 1. Objetivo

Definir o escopo verificável necessário para declarar o Radar Leilão 100% concluído no conjunto de fontes, modalidades, jurisdições e operações explicitamente suportadas.

## 2. Escopo funcional obrigatório

### A. Descoberta e radar
- [ ] Fontes cadastráveis com tipo, cobertura, termos de uso, autenticação e status.
- [ ] Ingestão manual e automatizada onde houver API/acesso autorizado.
- [ ] Captura de edital, lote, imóvel, preço, datas, modalidade e URL de origem.
- [ ] Deduplicação com resolução de identidade de imóvel e oportunidade.
- [ ] Atualização incremental e detecção de alterações.
- [ ] Histórico de captura, falhas, retries e proveniência.
- [ ] Filtros, busca, alertas e fila de triagem.
- [ ] Sem contornar CAPTCHA, autenticação, bloqueios ou restrições do portal.

### B. Property e Opportunity
- [ ] Entidade Property independente de Opportunity.
- [ ] Uma Property pode possuir múltiplas Opportunities.
- [ ] Cada Opportunity possui modalidade, origem, edital, preço, cronograma, status e workflow próprios.
- [ ] Isolamento completo de documentos específicos, análises, riscos, custos, decisões e transições por oportunidade quando aplicável.
- [ ] Compatibilidade com registros legados.
- [ ] Testes de não vazamento entre oportunidades do mesmo imóvel.

### C. Documentos e inteligência
- [ ] Upload seguro, hash, origem, tipo, versionamento e armazenamento persistente.
- [ ] OCR e extração com página/seção e confiança quando disponível.
- [ ] Classificação documental e detecção de documento ausente/desatualizado.
- [ ] Evidências ligadas ao trecho/página/versão real.
- [ ] Busca lexical/semântica com fallback transparente.
- [ ] Revisão humana e correção de extração.
- [ ] Histórico de reprocessamento sem sobrescrever versões anteriores.

### D. Jurídico
- [ ] Central Jurídica com fontes oficiais, legislação, atos e jurisprudência.
- [ ] Jurisdição, vigência, data de consulta, URL, versão e status de verificação.
- [ ] Separação entre texto legal, interpretação, orientação operacional e hipótese.
- [ ] Regras específicas por modalidade e contexto.
- [ ] Correlação de processos e partes quando fonte autorizada estiver disponível.
- [ ] Risco jurídico com evidência e fundamento.
- [ ] LLM não confirma sozinho impedimento ou hard stop.
- [ ] Revisão humana para conclusões críticas e dados jurídicos incertos.

### E. Due diligence
- [ ] Checklist dinâmico por modalidade, imóvel, jurisdição e contexto.
- [ ] Preservação integral dos 27 canonical_key históricos.
- [ ] Estado, aplicabilidade, dispensa justificada, evidência, responsável e prazo.
- [ ] Pendências bloqueantes e não bloqueantes.
- [ ] Snapshot/versionamento do checklist executado.
- [ ] Reabertura/invalidação quando fato relevante mudar.

### F. Financeiro e mercado
- [ ] Custo de aquisição e custo total de investimento.
- [ ] Comissão, tributos, débitos, condomínio, IPTU, cartório, honorários e despesas operacionais.
- [ ] Reforma, desocupação, regularização, carregamento e contingência.
- [ ] Cenários pessimista/base/otimista e sensibilidade.
- [ ] Fluxo de caixa, ROI, margem, TIR, yield, payback e preço máximo de lance.
- [ ] Parâmetros com jurisdição, fonte, vigência e versão.
- [ ] Comparáveis de venda/locação, liquidez e estimativa de valorização.
- [ ] Separação clara entre preço observado, estimativa e valor confirmado.
- [ ] Cálculos determinísticos e reproduzíveis, com testes de referência.

### G. Decisão e workflow
- [ ] Workflow F0–F13 e fluxos alternativos.
- [ ] Transições validadas por regras determinísticas.
- [ ] Gates obrigatórios e condicionais.
- [ ] Hard stops separados de score.
- [ ] Hipótese, validação, confirmação, resolução e descarte de risco.
- [ ] Aprovação com responsável, data, justificativa, evidências e snapshot.
- [ ] Invalidação sem apagar decisões passadas.
- [ ] Idempotência, concorrência e histórico append-only.
- [ ] Próxima ação, pendências e motivo de bloqueio visíveis.

### H. Aquisição e pós-arrematação
- [ ] Estratégia e limite máximo de lance aprovados.
- [ ] Agenda e regras do certame.
- [ ] Registro do resultado, inclusive não vencedor/sem lance/cancelado.
- [ ] Controle de comissão, sinal, parcelas, vencimentos e comprovantes.
- [ ] Controle documental e prazos de transferência/registro.
- [ ] Acompanhamento de posse, ocupação e medidas legais cabíveis.
- [ ] Débitos, regularização e pendências.
- [ ] Reforma, orçamento, fornecedores, cronograma e realizado.
- [ ] Eventos excepcionais: desistência, anulação, inadimplemento e reversão.

### I. Rentabilização e encerramento
- [ ] Estratégia: manter, alugar ou vender.
- [ ] Preparação do imóvel e custos.
- [ ] Controle de contratos, aluguel, vacância, inadimplência e manutenção.
- [ ] Controle de anúncio, proposta, venda, corretagem e tributos.
- [ ] Receitas/despesas e fluxo de caixa realizado.
- [ ] Comparativo projetado versus realizado.
- [ ] ROI, TIR e lucro realizado.
- [ ] Encerramento com documentação, motivo e resultado final.

### J. Plataforma, UX e operação
- [ ] Dashboard de radar, carteira, oportunidades, tarefas e resultados.
- [ ] Dossiê completo por oportunidade.
- [ ] Linha do tempo, próxima ação e bloqueios explicados.
- [ ] Pesquisa, filtros e relatórios exportáveis.
- [ ] Autenticação, RBAC e segregação de acesso.
- [ ] Auditoria de ações e alterações.
- [ ] Logs estruturados, métricas, tracing e alertas.
- [ ] Gestão de segredos e configuração por ambiente.
- [ ] Backup e restauração testados.
- [ ] CI/CD, migrations seguras e rollback.
- [ ] Runbooks, documentação e política de retenção.

## 3. Qualidade não funcional
- Integridade referencial e transacional.
- Idempotência em ingestão, jobs e transições.
- Concorrência segura e prevenção de duplicidade.
- Segurança contra upload malicioso, injection, exposição de segredo e acesso indevido.
- Performance medida nos volumes-alvo definidos.
- Observabilidade de falhas e custo de IA/integrações.
- Acessibilidade e usabilidade nos fluxos principais.
- Compatibilidade de API e versionamento.
- Recuperação testada de banco e arquivos.
- Privacidade e minimização de dados.

## 4. Critérios de exclusão explícita
Não é requisito do 100%:
- integração com todo portal existente no Brasil;
- scraping quando proibido ou tecnicamente bloqueado;
- automação de CAPTCHA ou bypass de controles;
- decisão jurídica autônoma sem validação adequada;
- protocolo real em cartório/órgão sem integração autorizada;
- garantia de valorização, liquidez, aluguel ou resultado;
- execução automática de lance/pagamento sem controles e autorização específicos.

Cada limitação deve estar documentada e visível ao usuário.

## 5. Evidências para declarar 100%
- Matriz de escopo com todos os itens e status.
- Relatório de testes unitários, integração, contrato, E2E e segurança.
- Evidência de fluxo completo para cada modalidade/fonte suportada.
- Evidência de isolamento e preservação de dados legados.
- Casos financeiros de referência reconciliados.
- Revisão jurídica de regras críticas e fontes.
- Evidência de backup e restore.
- Runbooks e documentação atualizados.
- Lista de limitações residuais aceita.
- Aprovação final do responsável pelo produto.

## 6. Regra de status
Um item não passa a CONCLUIDO por existir documentação ou código parcial. Exigir implementação integrada, teste aplicável, evidência e documentação. Se depende de fonte/credencial externa indisponível, marcar BLOQUEADO/DEPENDÊNCIA EXTERNA, nunca simular sucesso.
