# Checklist: primeiro imóvel real

Roteiro para a primeira homologação com um imóvel. **Comece com um imóvel fictício** (documentos sintéticos). Só use documentos reais depois de todos os gates da seção 0 e dos itens 1 a 11 passarem com o fictício.

Infra: ver `docs/04-operations/https-ocr-monitoramento.md`. Ativação da OpenAI: ver `PLANO-ATIVACAO-OPENAI.md`.

## 0. Gates (todos obrigatórios)

- [ ] Acesso por HTTPS (proxy com TLS) e `REQUIRE_HTTPS=true`; cookie de sessão `Secure`, `HttpOnly`, `SameSite`.
- [ ] Teto de gasto mensal definido **no painel da OpenAI** (o orçamento do app é segunda barreira, não a única).
- [ ] `LLM_BUDGET_USD_MONTH` e `LLM_BUDGET_USD_PER_ANALYSIS` definidos (valores baixos, ex.: 5 e 0,50).
- [ ] `llm_pricing` tem linha para o modelo de chat **e** o de embeddings (sem preço = bloqueio, `sem_preco`).
- [ ] `EMBEDDING_PRICE_PER_1M_USD` conferido contra a página de preços (padrão 0.02).
- [ ] Tesseract instalado no container do worker (`tesseract --version`, idiomas `por`).
- [ ] Backup do banco feito antes do teste.
- [ ] Todos os envolvidos sabem que nomes sem rótulo/cadastro, endereços, CNJ e CNPJ **seguem identificáveis** no que vai à OpenAI.
- [ ] Autorização formal para enviar o conteúdo do imóvel a provider externo (LGPD).

## 1. Cadastro
- [ ] Criar imóvel; preencher titular (`holder`) real/fictício exatamente como na matrícula (alimenta a pseudonimização).
- [ ] Cadastrar processos judiciais com polos (partes) e ocupantes, se houver.
- [ ] Conferir que não há 500 e que o status aparece correto.

## 2. Upload
- [ ] Enviar edital, matrícula e um PDF escaneado (um por vez).
- [ ] Documento aparece com estado correto; arquivo inválido/grande é rejeitado com mensagem clara.

## 3. OCR
- [ ] PDF escaneado vira texto (estado final "pronto"); OCR_MAX_PAGES respeitado.
- [ ] Documento ilegível termina em estado de erro/bloqueado, não "pronto".
- [ ] Memória do worker estável (OCR é uma página por vez).

## 4. Extração
- [ ] `POST /api/imoveis/{id}/extrair` com OpenAI **desligada**: resposta honesta (SEM_CHAVE), sem sucesso falso.
- [ ] Só depois de ativar: extração retorna campos; conferir manualmente cada valor.

## 5. Embeddings
- [ ] Chunks criados por versão pronta.
- [ ] Uma linha `agent='embedding'` em `llm_runs` por lote, tokens estimados e custo > 0.

## 6. RAG e isolamento
- [ ] Cadastrar um segundo imóvel fictício com documento distinto.
- [ ] Buscas do imóvel A nunca retornam trechos do B (conferir `source` das evidências).
- [ ] Reenviar nova versão de documento: só a última versão aparece nas evidências.

## 7. Agentes (um a um, OpenAI ativa, imóvel fictício)
- [ ] Documental
- [ ] Jurídico
- [ ] Financeiro
- [ ] Checklist (1 chamada batch de embeddings)
- [ ] Parecer/consolidação
- [ ] Após cada agente: conferir `llm_runs` (status, tokens, custo) e que o nome do titular nunca aparece como nome real no payload registrado (apenas `[TITULAR]`).

## 8. Análise completa
- [ ] Rodar análise completa; `LLM_BUDGET_USD_PER_ANALYSIS` não estourado.
- [ ] Forçar teto baixo: agentes restantes ficam `ORCAMENTO_EXCEDIDO` e o status da análise não é "sucesso".

## 9. Parecer consolidado
- [ ] Parecer coerente com os documentos; limitações e incertezas explícitas.

## 10. Conferência de evidências
- [ ] Cada finding cita trecho existente no documento certo.
- [ ] Findings com chunk inexistente foram descartados (sem 500).
- [ ] Nomes restaurados corretamente (sem `[TITULAR]` literal no parecer final).

## 11. Consumo e custos

Consulta de leitura:

```sql
SELECT agent, status, SUM(total_cost) AS custo, SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0)) AS tokens, MAX(created_at)
FROM llm_runs
GROUP BY agent, status
ORDER BY MAX(created_at) DESC;
```

- [ ] `GET /api/monitoring/rag` → `orcamento_llm` coerente com a soma acima.
- [ ] Custo do painel da OpenAI ≈ custo no app (diferença esperada: retries do SDK e estimativa de embeddings).

## Critérios de parada (remover `OPENAI_API_KEY` imediatamente)
- Custo real acima de 2x o esperado.
- Qualquer resultado de outro imóvel.
- Nome real aparecendo onde deveria haver papel pseudonimizado.
- 5xx recorrente ou worker travado.

## Rollback
1. Remover `OPENAI_API_KEY` e reiniciar backend e worker.
2. Revogar a chave no painel da OpenAI.
3. Restaurar backup do banco, se dados forem corrompidos.
