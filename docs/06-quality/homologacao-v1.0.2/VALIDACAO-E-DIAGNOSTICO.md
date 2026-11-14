# Validação local e diagnóstico de análises

Guia curto para validar a versão e investigar os primeiros testes com imóvel real e LLM real.

## 1. Validação local (sem OpenAI, sem custo)

```bash
# backend (PostgreSQL + pgvector), na raiz do repositório
python -m pytest -q tests
# frontend
cd frontend && npx tsc -b && npx vitest run && npx vite build
# caso sintético com gabarito (backend local rodando; nunca produção)
python -m pytest -q e2e/valor-negocio/test_scoring.py
python e2e/valor-negocio/valor_negocio.py --api http://127.0.0.1:8100 \
  --db postgresql://postgres@127.0.0.1:54329/<banco_local> --log <stdout do backend>
```

Esperado no `caso-01` (lance R$ 240.000): veredito **DESFAVORÁVEL / NÃO ARREMATAR**, preço máximo R$ 136.266,
prejuízo R$ 26.550, margem −7,9%, "O Radar responde à pergunta? SIM" e linha de base aprovada.

## 2. Como o veredito decide

Motor determinístico (sem LLM), em `backend/app/verdict_engine.py`:

1. Risco CRÍTICO ativo → DESFAVORÁVEL.
2. Operação financeiramente INVIÁVEL no lance pretendido → DESFAVORÁVEL (prejuízo, lance acima do preço máximo,
   meta de margem/ROI/lucro não atingida). Vale mesmo com custos desconhecidos tratados como zero: eles só
   melhoram a conta, então um resultado já ruim é ruim de verdade.
3. Outro risco ativo → ATENÇÃO.
4. Pendências, falta de evidência ou financeiro não comprovado → INCONCLUSIVO.
5. FAVORÁVEL só com cálculo COMPLETO (sem custos materiais desconhecidos), preço máximo DEFINITIVO, meta
   configurada e atendida, evidência e nenhuma pendência.

A ausência de IA aparece como fundamento próprio (`ANALISE_AUTOMATICA_INDISPONIVEL`) e nunca vira
inviabilidade financeira. Recomendação e fundamentos ficam em `veredito.financial.decisao`.

## 3. Diagnóstico de uma análise (JSON + Markdown)

Somente leitura. Junta, por análise: status e avisos, agentes (status, duração, provider, modelo, tokens,
custo, erro, chunks recuperados), chamadas do imóvel fora da análise (embeddings, extração), documentos e
estados, referências do RAG (documento, versão, página, seção, trecho), evidências, checklist e o veredito
com recomendação e fundamentos.

```bash
# no contêiner do backend (VPS) — analysis_id vem de GET /api/imoveis/{id}/historico
scripts/prod/compose.sh exec -T backend python -m app.diagnostics <analysis_id> --saida /tmp/diag
scripts/prod/compose.sh cp backend:/tmp/diag ./diag
# local, na raiz do repositório
PYTHONPATH=. DATABASE_URL=<url> python -m backend.app.diagnostics <analysis_id> --saida ./diag
```

Privacidade do diagnóstico: CPF, RG, e-mail, telefone e dados bancários mascarados; titular, partes e
ocupantes cadastrados viram papéis (`[TITULAR]`...); trechos cortados em 300 caracteres; nenhuma chave ou
configuração do provider é lida. Nomes soltos não cadastrados podem permanecer (sem NER).

Os logs do backend continuam passando pelo filtro de redação (segredos e dados pessoais) e trazem
`X-Request-ID`; `llm_runs` é a fonte de custo por chamada.
