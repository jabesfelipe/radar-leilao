# RADAR LEILÃO — CRITÉRIOS DE ACEITE MASTER

**Versão:** 1.0  
**Data:** 07/11/2026  
**Base:** ROADMAP-MASTER.md e PRODUCT-SCOPE-100.md

## 1. Estados e evidências
Cada capacidade terá estado, responsável, dependências, evidência e data:
`NAO_INICIADO`, `ESPECIFICADO`, `EM_DESENVOLVIMENTO`, `IMPLEMENTADO`, `VALIDADO`, `CONCLUIDO`, `BLOQUEADO`.

- ESPECIFICADO: documento aprovado e critérios claros.
- IMPLEMENTADO: código integrado, ainda sem validação completa.
- VALIDADO: testes e evidências passaram.
- CONCLUIDO: validado, documentado, operacional no escopo suportado e aceito.
- BLOQUEADO: dependência explícita; não contar como concluído.

## 2. Gates transversais obrigatórios
- G-01 Preservação: property 633, V1–V9, financial V1–V9, llm_runs, 27 canonical_key e Central Jurídica preservados.
- G-02 Isolamento: nenhuma leitura/escrita cruza Property/Opportunity indevidamente.
- G-03 Determinismo: workflow, gates e cálculos críticos não dependem de LLM.
- G-04 Auditoria: decisões, transições, versões e evidências não são apagadas nem sobrescritas.
- G-05 Compatibilidade: contratos existentes preservados ou mudanças versionadas e aprovadas.
- G-06 Segurança: autenticação/autorização, segredos, validação de entrada e proteção de arquivos testadas.
- G-07 Operação: logs, métricas, backup/restore, health e runbooks.
- G-08 Idempotência/concorrência: reprocessar ou repetir comando não duplica efeitos.
- G-09 Proveniência: fonte, versão, timestamp e confiança rastreáveis.
- G-10 Transparência: fato, inferência, hipótese, estimativa e orientação diferenciados.

## 3. Critérios por domínio

### Radar e ingestão
- Duplicidade detectada e resolvida de forma rastreável.
- Atualização não apaga valores anteriores; mudanças geram eventos.
- Falha de fonte fica observável e pode ser reprocessada.
- Fonte não autorizada não é acessada.

### Property/Opportunity
- Duas oportunidades do mesmo imóvel mantêm edital, preço, análise, workflow e decisão independentes.
- Consultas legadas sem opportunity_id continuam funcionando durante migração.
- Testes negativos demonstram ausência de vazamento cruzado.
- Identidade do imóvel não é confundida com identidade da oferta.

### Documentos/evidências
- Hash e versão persistidos.
- Extração aponta página/trecho somente quando disponível.
- Reprocessamento cria nova versão/resultado, sem sobrescrever histórico.
- Evidência inválida/obsoleta pode ser marcada e rastreada.

### Jurídico
- Toda regra crítica possui fundamento, jurisdição, vigência e fonte.
- Fonte desatualizada/inverificável não é apresentada como vigente.
- LLM gera hipótese, não confirmação final de hard stop.
- Conclusão crítica tem validação definida e auditável.

### Checklist/due diligence
- Os 27 canonical_key existentes continuam identificáveis.
- Checklist varia por modalidade/contexto sem destruir snapshots anteriores.
- Dispensa exige justificativa.
- Mudança de fato relevante invalida somente o que depende dela.

### Financeiro/valuation
- Fórmulas e arredondamentos documentados.
- Cenários reproduzíveis com mesmo input/versão de parâmetros.
- Custos confirmados e estimados diferenciados.
- Testes com casos de referência e reconciliação independente.
- Lance máximo respeita custos, margem mínima e hard stops.

### Workflow/decisão
- Transições válidas e inválidas testadas.
- Hard stop confirmado bloqueia mesmo com score alto.
- Hipótese de LLM não bloqueia automaticamente.
- Alteração de edital/matrícula/preço invalida aprovação afetada sem apagar a decisão anterior.
- Transições append-only, idempotentes e concorrência protegida.

### Aquisição/pós-arrematação
- Prazos e pagamentos geram alertas e trilha.
- Comprovantes e documentos associados à oportunidade correta.
- Resultado sem arrematação/cancelamento/fracasso também fecha o fluxo adequadamente.
- Registro e posse não são marcados concluídos sem evidência.

### Rentabilização
- Receitas/despesas realizadas conciliadas.
- Resultado final diferencia projeção de realizado.
- Venda/aluguel/holding têm fluxo de encerramento.
- Custos de reforma e operação entram no resultado.

### UX e operação
- Usuário identifica status, pendência, bloqueio, evidência e próxima ação.
- RBAC testado por perfil.
- Logs não expõem segredos/dados desnecessários.
- Backup é restaurado em ambiente isolado e validado.
- E2E cobre fluxo feliz e alternativos.

## 4. Testes mínimos obrigatórios
- Unitários por regra e cálculo.
- Integração para persistência e transação.
- Contrato OpenAPI.
- Migração upgrade/downgrade em banco descartável.
- Isolamento multi-oportunidade.
- Idempotência e concorrência.
- Segurança/autorização.
- E2E por modalidade/fonte suportada.
- Regressão do imóvel 633 sem criar novas análises.
- Restore de backup e verificação de integridade.

## 5. Política de release
Nenhuma fase será declarada concluída sem:
1. diff de código revisado;
2. testes executados e resultados registrados;
3. migrations revisadas;
4. documentação/status/histórico atualizados;
5. limitações conhecidas listadas;
6. evidência de preservação de dados;
7. commit rastreável.

## 6. Definição de 100%
100% somente quando todos os itens obrigatórios do PRODUCT-SCOPE-100 estiverem CONCLUIDOS ou houver exclusão formal aprovada com justificativa. Dependência externa não pode ser mascarada como concluída.
