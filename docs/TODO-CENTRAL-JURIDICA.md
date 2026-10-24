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
