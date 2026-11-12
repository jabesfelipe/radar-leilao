# MATRIZ DE CUSTOS, TRIBUTOS E EMOLUMENTOS

> **Fase Zero / diagnóstico.** Planejamento. Nada implementado. Mapeia os custos que o motor
> financeiro **já trata** contra o alvo do prompt (F7), cuja exigência central é
> **parametrização por jurisdição / ato / base / vigência / fonte oficial** — não constantes
> eternas. **Nenhuma alíquota/tabela abaixo é oficial**; valores anotados são **referências a
> validar**, nunca cadastrados como verdade.

## Como o motor financeiro trata custos hoje (`finance.py`)

Categorias de custo (fixas, em `COST_KEYS`): `aquisicao`, `comissao`, `itbi`, `registro`,
`debitos`, `condominio`, `iptu`, `custos_juridicos`, `desocupacao`, `reforma`, `carregamento`,
`outros`. O motor:
- calcula breakdown, custo total **sem dupla contagem** (Auction/Costs/Debts/Pós),
  resultado líquido de venda (corretagem + tributo parametrizável base GANHO/VENDA), margem,
  ROI da operação, yield, break-even e preço máximo (por meta);
- trata **dado ausente como `None` + pendência** (nunca zero silencioso); `preco_maximo` fica
  provisório quando há custos desconhecidos.

**Lacuna estrutural:** as categorias são fixas e **não** há parametrização por
jurisdição/ato/base/vigência/fonte, nem **TIR/VPL/fluxo descontado**, nem **grid de
sensibilidade** (só cenários BASE/OTIMISTA/PESSIMISTA).

## Matriz de itens de custo (alvo F7) × estado atual

| Item | Natureza | Depende de | Existe hoje? | Gap |
|---|---|---|---|---|
| Lance / arrematação | Aquisição | Resultado do leilão | ✅ `aquisicao` | — |
| Comissão do leiloeiro | % sobre arremate | Edital/leiloeiro | ✅ `comissao` | parametrizar % por edital |
| ITBI | Tributo municipal | Município, base, alíquota, vigência | ✅ `itbi` | **parametrizar por município/vigência** |
| Registro / escritura | Emolumento registral | UF, ato, tabela oficial | ✅ `registro` | **tabela de emolumentos por UF/ato/vigência** |
| Certidões | Custo registral/cartorial | UF/cartório | ⚠️ em `custos_juridicos`/`outros` | item próprio |
| Emolumentos / FUNREJUS / fundos / selo | Acessórios ao ato | UF, ato, tabela oficial | ❌ | **novo, por UF/ato/vigência** |
| ISSQN (quando incide) | Tributo municipal | Município | ❌ | validar incidência |
| IPTU em atraso | Dívida/tributo | Sub-rogação (CTN 130) / edital | ✅ `iptu`/`debitos` | vincular à sub-rogação |
| Condomínio em atraso | Obrigação propter rem | Convenção/edital | ✅ `condominio`/`debitos` | decompor principal/multa/juros/honorários |
| Dívida ativa / parcelamento | Fiscal | Município | ⚠️ `debitos` | modelar explicitamente |
| Advogado / honorários | Operacional | Fase/jurisdição | ✅ `custos_juridicos` | estimar por fase |
| Desocupação / mudança | Operacional | Caso concreto | ✅ `desocupacao` | separar mudança/ajuda |
| Custas processuais | Judicial | Jurisdição | ⚠️ `custos_juridicos` | item próprio (posse/imissão) |
| Reforma | CAPEX | Escopo/orçamento | ✅ `reforma` | vincular ao domínio de reforma (F11) |
| Regularização (habite-se/averbação) | Operacional | Município | ⚠️ `outros` | item próprio |
| Seguro / utilidades | Carregamento | Período de posse | ⚠️ `carregamento` | detalhar |
| Carregamento (condomínio/IPTU durante a posse) | Carregamento | Prazo | ✅ `carregamento` | — |
| Custo de capital | Financeiro | Taxa/prazo | ❌ | **novo (desconto/TIR)** |
| Corretagem na venda | Saída | % venda | ✅ (no resultado líquido) | — |
| IR ganho de capital | Tributo federal | PF/PJ, regime, requisitos | ⚠️ tributo parametrizável genérico | **condicional a PF/PJ/regime; validação contábil** |

## Parâmetros anotados (REFERÊNCIAS A VALIDAR — não são oficiais)

> O prompt (§5) registra números das anotações do usuário **explicitamente como "não fixar"**.
> Reproduzidos aqui **apenas como pendência de validação**, jamais como tabela cadastrada:
- **IR 15%** sobre ganho de capital, **reinvestimento em 180 dias** e **redutores por tempo**:
  **não fixar nem prometer** — depende de PF/PJ, regime e requisitos legais; exige validação
  contábil e base legal vigente.
- **FUNREJUS 0,2%** e teto anotado, **ISSQN**, **FUNDEP**, **selo**: **não cadastrar** sem
  **tabela oficial atual, ato, base e vigência**; evitar duplicidade com `registro`/`itbi`.
- **Taxa de ocupação 1% (art. 37-A)**: só após validar incidência, beneficiário, marco
  inicial/final, base e jurisprudência; **não presumir juros cumulados**.
- **Preço vil 50%**: avaliar no **judicial**; **não** usar como piso universal no extrajudicial.
- **Água/luz/gás**: separar **dívida pessoal** de obrigação eventualmente vinculada ao imóvel.

## Estrutura-alvo de parametrização (proposta — épico H, exige ADR)

Uma tabela de parâmetros fiscais/registrais com chave `(tributo_ou_ato, jurisdição, base,
vigência_inicio, vigência_fim, fonte_oficial)` e valor/alíquota, consumida pelo motor
financeiro em vez de constantes. Cada custo calculado deve carregar **memória de cálculo**:
fonte, data-base, vigência, parâmetro aplicado e nível de confiança (conhecido/estimado/
cotação pendente/contingência). **Nada entra sem fonte oficial e vigência.**

## Resumo

- 🟢 Motor financeiro determinístico robusto e anti-dupla-contagem **já existe** e é reutilizável.
- 🔴 **Parametrização por jurisdição/ato/vigência/fonte** é o maior gap (hoje: categorias fixas).
- 🔴 **TIR/VPL/fluxo descontado/sensibilidade** ausentes.
- ⚠️ Emolumentos/FUNREJUS/ISSQN/selo/IR: **só com tabela oficial vigente** — pendência, não dado.
