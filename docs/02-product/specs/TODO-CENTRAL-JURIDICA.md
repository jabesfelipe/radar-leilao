# TODO — Central Jurídica (pendências de curadoria e evolução)

Fundação da Central Jurídica entregue (migration `0017_central_juridica`, biblioteca
curada, referências contextuais, aba no dossiê, testes verdes). Este arquivo lista o
que falta amadurecer, para não perder rastreabilidade e **sem fabricar conteúdo**.

## P0 — Integridade de conteúdo

- [ ] **Base histórica "136 + 27 → 45 regras".** O material de origem (163 itens
  brutos normalizados em 45 regras canônicas) **não existe estruturado no código** —
  hoje a base implementada é o Checklist Mestre com 27 `canonical_key`. Recuperar o
  material-fonte (livro/planilha) e, se confirmado, cadastrar as regras/itens
  faltantes como `LegalRule`/`LegalRuleChecklistLink` preservando a rastreabilidade.
  Enquanto o material não for localizado, **não inventar** as 45 regras.
- [ ] **Curadoria jurídica dos textos oficiais.** Os `official_text` já cadastrados
  são transcrições curtas dos dispositivos vigentes. Revisar com fonte oficial
  (Planalto/tribunais), completar §§/incisos relevantes e promover
  `verification_status` para `VERIFICADO` apenas após conferência humana.

## P1 — Cobertura da base legal

- [ ] Ampliar dispositivos por fonte (ex.: Lei 9.514/97 art. 26 §§ e art. 27 §§
  completos; CPC arts. 879–903 sobre alienação; súmulas/temas repetitivos do STJ
  sobre alienação fiduciária, taxa de ocupação e imissão na posse).
- [ ] Cadastrar **jurisprudência** (`source_type=JURISPRUDENCIA`/`SUMULA`) com
  identificação do julgado e link oficial — sempre marcada como `PENDENTE` até
  conferência.
- [ ] Vincular regras aos demais `canonical_key` ainda sem base legal associada
  (checar `cobertura_checklist` em `GET /api/juridico/biblioteca`).

## P2 — Busca semântica (RAG)

- [ ] Rodar o seed com `embed=True` em ambiente com `OPENAI_API_KEY` para indexar os
  `KnowledgeItem` (kind `LEGAL_LIBRARY`) e habilitar busca vetorial em produção.
- [ ] Job/endpoint administrativo para (re)gerar embeddings quando textos mudarem.

## P3 — Integração contextual mais profunda

- [ ] Exibir "Base legal e orientações" diretamente dentro de cada item na aba
  Checklist (consumindo `GET /api/juridico/referencias/checklist/{key}`).
- [ ] Referências por etapa na aba Pós-Arrematação/Desocupação
  (`.../referencias/contexto/{DESOCUPACAO|POSSE|...}`).
- [ ] Opcional: anexar a base legal pertinente ao Veredito como contexto de leitura
  (sem alterar o motor de risco/veredito).

## P4 — Governança

- [ ] Campo de autoria/revisão por dispositivo (quem verificou, quando) para
  auditoria da curadoria.
- [ ] Marcar normas revogadas/alteradas como `DESATUALIZADO` mantendo histórico.


## P5 — Integração com a plataforma completa (06/11/2026)
- [ ] Levar conhecimento jurídico contextual a todas as fases, sem duplicar módulos existentes.
- [ ] Aplicabilidade por modalidade judicial/extrajudicial, etapa, jurisdição e fatos.
- [ ] Vincular dispositivos a evidências, critérios, consequências, riscos e providências.
- [ ] Separar verificação da fonte, vigência, transcrição, interpretação e aplicação.
- [ ] Integrar base a Checklist, Due Diligence, Ocupação, Pós-Arrematação, Financeiro e workflow.
- [ ] Versionar normas, regras, jurisprudência e decisões.
- [ ] Preservar 27 canonical_key.
- [ ] Ver docs/TODO-PLATAFORMA-COMPLETA.md e docs/PROMPT-KIRO-PLATAFORMA-COMPLETA.md.

## P5.1 — Mapa de curadoria da Fase Zero (diagnóstico)
- [ ] Usar `docs/MATRIZ-CURADORIA-JURIDICA.md` como mapa de gaps da Central Jurídica 1.0 → 2.0
  (vigência estruturada, redação histórica, jurisprudência com número/órgão/tese/data/fonte,
  aplicabilidade APLICAVEL/CONDICIONAL/APENAS_REFERENCIA/NAO_APLICAVEL/INDETERMINADO,
  revisor/próxima revisão). Normas-alvo e status de cadastro estão tabelados lá.
- [ ] Tratar a Central Jurídica 2.0 como **épico E** do `docs/ROADMAP-PLATAFORMA-COMPLETA.md`
  (depende de D — checklist dinâmico — e alimenta F3/F6/F8). Migration aditiva prevista `0021`.
- [ ] Recuperar "136 + 27 → 45 regras" do material-fonte antes de cadastrar; **não fabricar**.
