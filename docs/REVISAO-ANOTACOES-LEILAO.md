# REVISÃO DAS ANOTAÇÕES DE LEILÃO (backlog, não verdade pronta)

> **Fase Zero / diagnóstico.** Planejamento. Nada implementado. Consolida a §5 do
> `PROMPT-KIRO-PLATAFORMA-COMPLETA.md`: as anotações do usuário são **pistas/backlog**, não
> fatos nem integrações aprovadas. **Nenhuma integração externa, scraping ou consulta paga
> deve ser feita sem autorização, credenciais e limites.** URLs abaixo são **candidatas a
> avaliação**, não endossos.

## 1. Portais de leilão (diretório de origem/descoberta — F0)

| Portal | URL anotada | O que validar antes de qualquer integração |
|---|---|---|
| Biasi Leilões | https://www.biasileiloes.com.br/ | legitimidade, cobertura, **termos de uso**, acesso, existência de API |
| Globo Leilões | https://globoleiloes.com.br | idem |
| Bidmap | https://bidmap.com.br | idem |
| Spy Leilões | https://www.spyleiloes.com.br | idem |

- **Regra:** sem **scraping não autorizado**. Avaliar se há API oficial, termos que permitam
  uso automatizado, rate limits e custo. Enquanto não validado → **cadastro/importação manual**
  (como já é o padrão das frentes de due diligence sem credencial → `NAO_CONFIGURADO`).

## 2. Registro de imóveis eletrônico (F3 — matrícula)

| Serviço | URL anotada | Validar |
|---|---|---|
| Registro24 | https://www.registro24.com.br/ | oficialidade, cobertura, custo, **autorização** |
| RI Digital | (referência do `.env.example`: ridigital.org.br) | idem |

- **Estado atual:** `REGISTRO_IMOVEIS_*` existe no `.env.example` como integração **opcional**;
  sem credencial, a matrícula segue por **importação manual de PDF/certidão com OCR** (já
  implementado). Não há API pública gratuita — integração exige contratação/autorização.

## 3. Notificação extrajudicial / RTD (F6 — posse)

| Serviço | URL anotada | Validar |
|---|---|---|
| RTD Brasil | https://www.rtdbrasil.org.br/ | serviço, **prova de entrega**, requisitos legais |

- **Regra:** minuta de notificação é **rascunho para advogado** (já modelado em
  `NotificationDraft*`). Prova de entrega/forma exige validação jurídica; não presumir
  recebimento/cumprimento de prazo sem comprovante.

## 4. Serviços de desocupação (F6/F11)

| Serviço | URL anotada | Validar |
|---|---|---|
| Desocupação Leilões | https://desocupacaoleiloes.com.br/ | legitimidade, escopo, custo, contrato |
| Desocupa Simples | https://desocupasimples.com.br | idem |
| Mestre dos Leilões | https://www.mestredosleiloes.com/ | legitimidade, natureza (conteúdo × serviço) |

- **Regra:** proibida autotutela (coerção, corte de serviços, entrada forçada). Consultoria de
  desocupação já modelada (`Consultancy*`), com escopo incluído/excluído explícito.
- **Instagram/Drive não são fonte normativa.**

## 5. Teses e parâmetros jurídico-financeiros (tratar como hipótese a validar)

| Anotação | Tratamento exigido pelo prompt |
|---|---|
| **Usufruto** | **Alerta crítico.** Óbito alegado **não** basta para presumir extinção; conferir certidão, registro e **cancelamento** na matrícula. |
| **IR 15% / reinvestimento 180 dias / redutores por tempo** | **Não fixar nem prometer.** Depende de PF/PJ, regime e requisitos; exige validação contábil e base legal vigente. |
| **FUNREJUS 0,2% + teto / ISSQN / FUNDEP / selo** | **Não cadastrar** sem tabela oficial atual, ato, base e vigência; evitar duplicidade. |
| **Taxa de ocupação 1% (art. 37-A)** | Validar incidência, marco inicial/final, base, legitimidade e jurisprudência; **não presumir juros cumulados**. |
| **Preço vil 50%** | Avaliar no **judicial**; **não** usar como piso universal no extrajudicial. |
| **Inquilino / liminar** | Validar contrato, averbação, modalidade e pressupostos; **não prometer liminar**. |
| **Água/luz/gás** | Separar **dívida pessoal** de obrigação vinculada ao imóvel. |
| **Certidões** | Matriz contextual: **negativa não garante imóvel livre**; registrar o que prova e o que não prova. |
| **Negociação / ajuda de mudança** | Voluntária, documentada, aprovada e condicionada (consentimento livre, acordo escrito, entrega de chaves, vistoria, quitação). |
| **Honorários / custas** | Estimativas por fase/jurisdição e cotações; **sem ameaça ao ocupante**. |
| **Fotos / vídeos** | Registrar origem, data, legitimidade e limites. |

## 6. Como estas anotações entram no roadmap

- **Portais (F0):** épico M (integrações) — só após validação de termos/API/autorização;
  fallback manual permanece.
- **Registro/Prefeitura (F3/F4):** épico F/M — manual até credencial autorizada.
- **RTD/desocupação (F6/F11):** épicos G/K — serviços como fornecedores cadastráveis, não
  automações de autotutela.
- **Teses/parâmetros (§5):** épicos E (Central Jurídica 2.0) e H (custos parametrizados) —
  **sempre** com fonte oficial e vigência; nada fixado como constante.

## 7. Princípio final

Toda anotação é **entrada de backlog**. Antes de virar código/integração/parâmetro, passa por:
(1) validação de **legitimidade/autorização/termos**; (2) **fonte oficial** quando for norma/
tributo; (3) **ADR** quando exigir nova integração/tabela. Sem isso, permanece como **pendência
documentada**, nunca como funcionalidade declarada.
