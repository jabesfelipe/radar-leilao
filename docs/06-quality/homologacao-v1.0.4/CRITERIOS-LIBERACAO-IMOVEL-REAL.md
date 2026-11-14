# Critérios de liberação para imóvel real — situação na v1.0.4

Marcado só o que foi **demonstrado** (execução real com o caso sintético `caso-01` e/ou teste automatizado no
PostgreSQL real). Detalhes e números em [HOMOLOGACAO-QUALIDADE-IA.md](HOMOLOGACAO-QUALIDADE-IA.md).

## Extração
- [x] Matrícula extraída com referências válidas (execução real: número, cartório, comarca, data, titular).
- [x] Edital extraído com referências válidas (verificação real dirigida: 5 campos). `notice_date` falhou por ponteiro de
      chunk — causa corrigida e testada, **sem nova execução real completa após a correção**.
- [x] Campos sem evidência ficam INCONCLUSIVO/NAO_ENCONTRADO com motivo, nunca preenchidos.
- [ ] Páginas rastreáveis em PDF real com várias páginas: validado só com texto sintético (sem número de página).

## Evidências
- [x] Nenhuma citação inventada aceita como prova (100% válidas; T6 = 0 nas execuções após a correção).
- [x] Nenhuma pergunta de checklist como evidência (validador + testes negativos).
- [x] Origem identificada (DOCUMENTO, CADASTRO, CALCULO, PESQUISA_JUDICIAL, INFERENCIA_IA, REGRA_DETERMINISTICA).
- [x] Documento e chunk rastreáveis; isolamento A × B validado em execução real e em testes.

## Checklist
- [x] Item resolvido tem origem registrada (`resolution_origin`) e, se documental, evidência FORTE/MODERADA vinculada.
- [x] Item calculado (lance < 50%, prazo, comparáveis) só pela regra determinística.
- [ ] Explicação textual do motivo de cada item pendente na interface (hoje: "pendente" sem justificativa por item).

## Inteligência
- [x] Fatos críticos identificados (penhora, indisponibilidade, ocupação) em todas as execuções.
- [x] Divergência de área matrícula × edital apresentada com as duas fontes (confronto determinístico).
- [x] Falhas de agente aparecem (`AGENTES_PARCIAIS`, 4/5, observado e exibido).
- [ ] Cobertura estável: 12 a 15 de 20 pontos entre execuções; comissão + pagamento à vista (F7) e venda *ad corpus*
      (F9) ainda falham com frequência.

## Financeiro
- [x] Preço máximo, prejuízo, margem e ROI iguais ao gabarito; veredito determinístico; motivos explícitos.
- [x] Custos desconhecidos não produzem FAVORÁVEL (regra do `verdict_engine.py`, inalterada).

## Segurança
- [ ] **HTTPS validado no ambiente externo** — não verificado (sem acesso à VPS); configuração de produção do
      repositório publica só a porta 80. **Bloqueador.**
- [ ] **`REQUIRE_HTTPS=true` no ambiente protegido** — depende do item anterior. **Bloqueador.**
- [x] Chave ausente de logs, relatórios e cópias (varredura por valor exato e trecho interno).
- [x] Dados pessoais minimizados no que chega ao provider (teste de payload); endereço, matrícula, processo e CNPJ
      enviados por necessidade (decisão documentada).
- [x] Orçamento persistente: `.env` local e `.env.prod.example`; `LLM_REQUIRE_BUDGET=true` no compose de produção.
- [ ] Orçamento persistente **na VPS** — não aplicado (sem acesso).
- [x] Limites testados com a OpenAI real (por análise: bloqueia, excedendo no máximo uma chamada; mensal: 0 chamadas).

## Operação
- [x] Backend completo e frontend (tsc, vitest, build) aprovados.
- [ ] E2E Playwright (desktop/mobile) não reexecutado nesta versão.
- [x] Diagnóstico por análise disponível (`llm_runs` por agente com tokens, custo, status e motivo de bloqueio).
- [x] Rollback: a migration 0025 só adiciona colunas opcionais (`downgrade` remove); demais mudanças são de código.

**Classificação: B — liberado somente para documentos sintéticos.** Os bloqueadores para imóvel real são HTTPS na VPS
(com `REQUIRE_HTTPS=true`) e a aplicação do orçamento persistente na VPS.
