# Fluxo de evidências do checklist (v1.0.11, `evidencias-v1`)

Como uma informação de documento chega a um item do Checklist Mestre, e como a resposta fica rastreável.

## Fluxo

```
DOCUMENTO (upload) ──► DocumentPipeline: texto (OCR quando preciso) ► DocumentChunk (página, seção)
   │
   ├─ MATRICULA ─────► registry_chain.read_registry: atos R-n/Av-n em ordem, fatos com trecho e ato
   │                     (alienação, consolidação, ônus, cancelamentos, leilões, intimação, locação, vaga, ação, garantia)
   │                   services.persist_registry_findings: uma Evidence DOCUMENTO por fato (trecho literal, chunk, página)
   │                   services.resolve_checklist_from_registry ► checklist_evidence.resolve_registry_items
   │
   ├─ CONDICOES_VENDA / EDITAL ► sale_conditions.read_conditions: cláusulas de condomínio, IPTU/tributos, evicção,
   │                     FGTS e pagamento, cada uma com trecho e regra classificada
   │
   └─ módulos do Radar: ocupação, processos, localização, comparáveis (inteligência de mercado), premissas, dívidas
                       │
                       ▼
     checklist_evidence.resolve_checklist_evidence ► ChecklistResult (estado, conclusão, fundamentação, regra)
                       │                              + ChecklistEvidence (vínculo com cada evidência usada)
                       ▼
     risk_engine (RISCO_IDENTIFICADO → ALTA, ATENCAO → MEDIA, só com evidência) ► verdict_engine (fatores)
```

Ordem na análise (`POST /api/imoveis/{id}/analisar` e reanálise incremental): agentes de IA (quando há chave) →
cadeia registral → dados cadastrados (`resolve_checklist_from_data`) → `resolve_checklist_evidence` → riscos → veredito.
Uma resposta já dada (usuário, agente com citação validada ou regra anterior) nunca é sobrescrita: só itens aplicáveis em
PENDENTE ou EM_ANALISE são tocados.

## Onde a informação deixava de chegar (diagnóstico da v1.0.10)

Na análise v4 do imóvel 7 (venda direta), 24 dos 27 itens ficaram PENDENTE porque:

1. A cadeia registral só alimentava os itens 9 (consolidação) e 10 (penhora, só quando encontrada). Os fatos lidos da
   matrícula (R-3, Av-5, a certidão "pós edital", o mútuo da própria aquisição, a dívida garantida) não chegavam aos itens
   1–5, 8, 12 e 16.
2. A ausência de penhora era tratada sempre como "não responde o item", mesmo com a matrícula lida inteira.
3. Não existia leitura das condições oficiais da venda: os itens 14 e 15 dependiam de edital (que a venda direta não tem)
   ou das premissas digitadas pelo usuário (no imóvel 7 em produção, não cadastradas).
4. Ocupação, localização, inteligência de mercado e premissas não eram consultadas pelo checklist (só comparáveis 7+7,
   prazo e 2º leilão).
5. Os itens que ficavam pendentes repetiam a mesma justificativa genérica (itens 1–5) ou nenhuma.

## Modelo de evidência

`Evidence` (sem migration; campos existentes desde a 0025): `document_version_id`, `chunk_id`, `page`, `section`,
`source_excerpt` (trecho literal), `fact` (o que a regra concluiu), `origin`, `strength`, `confidence`, `agent`, `created_at`.
O vínculo com o item é `ChecklistEvidence`; com a análise, `EvidenceLink(target_type="Analysis")`.

| `origin` | Tipo exibido | Exemplo |
|---|---|---|
| DOCUMENTO (categoria ≠ CONDICOES_VENDA) | Fato documental | "Intimação por edital mencionada (Av-5)", com o trecho da matrícula |
| DOCUMENTO (categoria CONDICOES_VENDA) | Regra oficial da venda | regra de condomínio, com o trecho das condições |
| CALCULO / REGRA_DETERMINISTICA | Cálculo | liquidez estimada pelos comparáveis |
| INFERENCIA_IA | Inferência da IA | afirmação de agente sem citação válida |
| CADASTRO | Informação fornecida pelo usuário | cadastro de ocupação, checklist de localização, premissa de reforma |
| NAO_LOCALIZADA (nova, v1.0.11) | Informação não localizada | "Matrícula examinada (atos lidos: Av-1, R-2, R-3, Av-4, Av-5): nenhum registro de penhora…", com o documento examinado e sem trecho |

Evidência sem origem verificável nunca confirma item jurídico. A conclusão da regra fica em `fact`; o trecho original fica em
`source_excerpt` e nunca é substituído.

## API

- `GET /api/imoveis/{id}/checklist` e `GET /api/imoveis/{id}`: cada item traz `question` (adequada à modalidade),
  `pergunta_catalogo`, `resultado`, `resultado_label`, `acao_recomendada`, `fonte_necessaria`, `grupo`, `evidence_ids`.
  Campos derivados do que está gravado: análises anteriores ganham os mesmos campos, sem reprocessar.
- `GET /api/imoveis/{id}/checklist/{resultado_id}/evidencias`: as evidências do item com documento, versão, página, seção,
  trecho, tipo, confiança, responsável (agente ou regra) e data. Dados pessoais mascarados na exibição.

## Limites conhecidos

- A leitura das condições da venda reconhece as redações de limite "paga o que exceder" e "assume integralmente acima do
  limite"; outras redações ficam INCONCLUSIVO com o trecho para leitura humana.
- A data da cópia da matrícula não é verificada: "sem restrição identificada" sempre pede certidão atualizada.
- "Grande reforma" (item 21) usa a referência de análise `checklist.reforma_grande_pct` (padrão 10% da aquisição), ajustável
  por imóvel ou no catálogo de parâmetros. Não é regra jurídica.
- O condomínio do próprio imóvel, a Selic de referência, o endereço do investidor e a portaria do condomínio não são
  cadastrados no Radar: os itens 18, 22, 24 e 26 ficam pendentes com a ação.
