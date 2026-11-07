# MATRIZ DE CURADORIA JURÍDICA (Central Jurídica 1.0 → 2.0)

> **Fase Zero / diagnóstico.** Planejamento. Nada implementado. Mapeia a base legal **já
> cadastrada** (Central Jurídica 1.0, migration `0017`) contra a **Central Jurídica 2.0** do
> prompt (§4). **Regra absoluta: nunca inventar norma, artigo, redação ou julgado.** O que não
> foi conferido na fonte oficial fica como `PENDENTE`/`INDETERMINADO`.

## Estado atual da Central Jurídica (1.0)

Modelos (migration `0017_central_juridica`): `LegalSource`, `LegalProvision` (texto oficial
**separado** da paráfrase prática), `LegalRule`, `LegalRuleChecklistLink` (enriquece os 27
`canonical_key` sem alterá-los). Serviço `legal_service.py` + catálogo `legal_catalog.py` +
busca na biblioteca (reusa embeddings/`KnowledgeItem`). Endpoints `GET /api/juridico/biblioteca`,
`.../busca`, `.../referencias/checklist/{key}`, `.../referencias/contexto/{ctx}`.

Conteúdo curado existente (conforme `docs/CENTRAL-JURIDICA.md`): Lei 9.514/97 (arts. 26, 27,
37-A), Código Civil (1.228, 447), CPC/2015 (903), Lei 8.245/91 (8º), CTN (130, 131).

## O que a 2.0 exige por norma (prompt §4) × o que existe

| Metadado da 2.0 | Existe na 1.0? | Gap |
|---|---|---|
| Identificação oficial (lei/código) | ✅ `LegalSource` | — |
| Artigo/parágrafo/inciso | ✅ `LegalProvision` | — |
| Texto oficial (verbatim) | ✅ (separado da paráfrase) | — |
| Link primário | ✅ `official_url` | validar que é fonte oficial |
| Publicação / vigência | ⚠️ parcial | **estruturar vigência (início/fim)** |
| Alterações / redação histórica | ❌ | **novo (versões da redação)** |
| Contexto / fatos necessários / exceções | ⚠️ parcial (`practical_note`) | estruturar |
| Controvérsias / jurisprudência | ❌ | **novo (julgado estruturado)** |
| Orientação prática separada | ✅ `practical_note` | — |
| Evidências requeridas | ⚠️ via `LegalRuleChecklistLink` | ampliar |
| Efeito operacional/financeiro | ⚠️ parcial | estruturar |
| Confiança / revisor / data / próxima revisão | ❌ | **novo (governança de curadoria)** |
| Aplicabilidade (APLICAVEL/CONDICIONAL/APENAS_REFERENCIA/NAO_APLICAVEL/INDETERMINADO) | ❌ | **novo (por modalidade/jurisdição)** |

## Mapa de normas-alvo (prompt §4) × status de curadoria

> Status: ✅ cadastrado (1.0) · 🟡 cadastrado parcialmente · 🔴 a cadastrar (pendência). Fonte
> oficial prioritária: Planalto, Diário Oficial, tribunais, CNJ, órgãos fiscais, Corregedorias.

| Norma | Relevância no workflow | Status |
|---|---|---|
| **Lei 9.514/97** (alienação fiduciária; arts. 26, 27, 37-A) e alterações | F1/F3/F6 — núcleo do extrajudicial | 🟡 (arts. 26/27/37-A cadastrados; falta vigência/alterações/redação histórica) |
| **Código Civil** (propriedade, posse, evicção — arts. 1.228, 447) | F3/F6 | 🟡 |
| **CPC/2015** (arrematação judicial — art. 903) | Trilha judicial (separada) | 🟡 |
| **Lei 8.245/91** (locação; denúncia, preferência, averbação — art. 8º) | F6 | 🟡 |
| **CTN** (sub-rogação/responsabilidade — arts. 130, 131) | F4/F7 | 🟡 |
| **Lei 6.015/73** (registros públicos) | F3/F10 | 🔴 |
| **Emolumentos / CNJ / Corregedoria** (atos registrais e custos) | F7/F10 | 🔴 |
| **Lei 4.591/64** (condomínio e incorporação) | F4 | 🔴 |
| **Lei 13.465/17** (regularização fundiária) | F11 | 🔴 |
| **Normas urbanísticas/ambientais estaduais/municipais** | F4/F5 | 🔴 (por jurisdição) |
| **Jurisprudência STF/STJ/TJs** (teses sobre A.F., taxa de ocupação, imissão, preço vil) | F3/F6/F8 | 🔴 (só com número/órgão/tese/data/fonte oficial) |

## Regras de integridade da curadoria (do prompt)

1. Separar **verificação da fonte · vigência · transcrição · interpretação · aplicação**.
2. Site privado é **pista**, não fonte final. Instagram/Drive **não** são fonte normativa.
3. **Nunca** inventar julgado ou texto não conferido. Jurisprudência só entra com **número,
   órgão, tese, data, situação e fonte oficial**.
4. Aplicabilidade sempre qualificada por **modalidade/etapa/jurisdição/fatos**.
5. Registrar **revisor, data e próxima revisão**; manter **histórico de alterações** da redação.

## Pendências priorizadas (épico E)

- **P0:** estruturar `vigência` (início/fim) e `aplicabilidade` nos modelos legais; registrar
  revisor/próxima revisão.
- **P0:** auditar cobertura dos 27 `canonical_key` pela base legal (há `checklist_reference_map`).
- **P1:** adicionar entidade de **jurisprudência** estruturada (número/órgão/tese/data/fonte).
- **P1:** cadastrar Lei 6.015/73, Lei 4.591/64, Lei 13.465/17 e emolumentos/CNJ.
- **P2:** redação histórica (versões do texto) e trilha de alterações normativas.
- **Pendência herdada:** recuperar "136 + 27 → 45 regras" do material-fonte (não fabricar).
