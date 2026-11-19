# Inteligência do imóvel (v1.0.12, não publicada)

Evolução aprovada em seis fases. Tudo é determinístico (sem IA), reaproveita os módulos existentes e não cria tabelas.

## Fase A — Fonte única de custos (condomínio e IPTU em atraso)

`viability.debt_exposure` e `viability.caixa_rules` alimentam a composição de custos. A composição é a mesma para o veredito,
a inteligência de mercado, a recomendação e o checklist (item 15).

| Ordem | Fonte do valor da dívida | Como entra |
|---|---|---|
| 1 | Dívida confirmada (Central de Débitos `CONFIRMADO` ou legado `CONFIRMADO`) | valor da dívida |
| 2 | Dívida informada (legado, Central de Débitos `INFORMADO`/`PENDENTE` com valor, custo cadastrado) | valor da dívida |
| 3 | Estimativa condominial (última `CondominiumEstimate`) | provável no cenário base; alto no conservador |
| 4 | Sem valor | fora da soma no base; teto de responsabilidade no conservador |

Consulta `INDISPONIVEL` ou `EM_VALIDACAO` nunca vira zero.

Regra de responsabilidade: documento das condições da venda (trecho literal) > premissa `condicoes_caixa` > sem regra.
A regra é aplicada depois do valor. Cada linha mostra dívida potencial, dívida confirmada, parte do comprador, parte do
vendedor, limite e valor considerado por cenário.

Item 08 (leilões negativos): a linha "Averbação dos leilões negativos: <situação>" das condições da venda entra como
informação do vendedor. O item fica INCONCLUSIVO: a declaração não comprova a averbação, que só a matrícula atualizada mostra.

Veredito: pendências financeiras agrupadas por assunto (valor de venda, meta, débitos, ocupação, custos, premissas de venda,
jurídico, lance). Nenhuma mensagem é perdida; as repetidas ficam em `detalhes`.

## Fase B — Premissas financeiras no Admin

Admin > Premissas financeiras mostra o catálogo de parâmetros nas categorias `financeiro` e `estimativa`, com o mesmo
histórico e versionamento da aba Parâmetros. Também permite cadastrar um valor por município (escopo `MUNICIPIO`), como a
alíquota de ITBI.

Prioridade no cálculo: valor do imóvel > consulta ou documento > estimativa calculada > catálogo (Admin) > pendente. O padrão
global nunca sobrescreve um valor do imóvel. A origem aparece em cada linha.

Padrões existentes (mesmo valor que o motor já usava; o seed não muda nenhum cálculo):

| Chave | Valor |
|---|---|
| `venda.corretagem_pct` | 0,06 |
| `venda.tributo_ganho_pct` | 0,15 |
| `venda.prazo_meses` | 12 |
| `viabilidade.roi_minimo` | 0,20 |
| `viabilidade.reserva_registro_pct` | 0,02 |
| `viabilidade.reserva_certidoes` | R$ 600 |
| `viabilidade.reserva_reforma_m2` | R$ 250/m² |
| `viabilidade.reserva_reforma_m2_base` | R$ 100/m² |
| `viabilidade.reserva_desocupacao` | R$ 5.000 |
| `checklist.reforma_grande_pct` | 0,10 |
| `cenario.prazo_conservador_fator` / `cenario.prazo_otimista_fator` | 1,5 / 0,75 |
| `aluguel.taxa_ocupacao` / `aluguel.taxa_administracao` | 0,90 / 0,10 |
| `mercado.desconto_negociacao` / `mercado.similaridade_minima` | 0,10 / 0,50 |

Novos parâmetros:

| Chave | Valor inicial | Uso |
|---|---|---|
| `viabilidade.fator_venda_avaliacao` | 0,85 | valor de venda preliminar (decisão 2.2) |
| `viabilidade.margem_minima` | 0,10 | ressalva quando a margem do cenário base fica abaixo |
| `viabilidade.margem_seguranca_minima` | 0,10 | ressalva quando a margem de segurança fica abaixo |
| `viabilidade.itbi_aliquota` | sem valor | ITBI; preencher com fonte oficial, de preferência por município |
| `viabilidade.regularizacao_padrao` | sem valor | reserva de regularização |
| `iptu.valor_anual_padrao` | sem valor | IPTU anual durante a posse |
| `viabilidade.custos_mensais_padrao` | sem valor | custo mensal da posse |
| `condominio.valor_mensal_referencia` | sem valor | taxa condominial mensal de referência |

Itens sem valor continuam pendentes até o operador preencher: o sistema não inventa ITBI, IPTU nem condomínio.

### Valor de venda preliminar (decisão 2.2)

Sem valor de venda informado e sem comparável usável, o cenário base usa
`valor preliminar = avaliação do vendedor × viabilidade.fator_venda_avaliacao` (0,85). O resultado leva o selo "Estimativa
preliminar", confiança Baixa, a fórmula e a origem do fator. O cálculo do veredito fica provisório. Com comparáveis, o fator não é
usado. O usuário substitui o valor em Financeiro > Premissas.

## Fase C — Linha do tempo da matrícula

`GET /api/imoveis/{id}/matricula/linha-do-tempo` lê a última matrícula com texto (`registry_chain`, sem reprocessar e sem
gravar). Cada ato reconhecido no início de linha (R-n, Av-n), mais a abertura, vira um evento com:

- data: a primeira data válida citada no ato (protocolo ou título), com o texto literal;
- tipo: pelo título do ato (compra e venda, alienação fiduciária, conclusão de obra, consolidação, cancelamento, penhora...);
- partes: só com papel declarado no texto (rótulo "VENDEDORA:", "vendeu a", "em favor de", "em nome da credora"); papéis:
  proprietário anterior, comprador, vendedor, devedor, credor, outros. Nenhum papel é inferido;
- valor (preço, dívida ou valor citado), construtora, conclusão de obra, trecho, documento, página e fonte.

Nomes de pessoas físicas aparecem só para usuário autenticado (todas as rotas passam pelo portão de autenticação) e sem CPF
ou outros documentos (`privacy.redact_pii`). Idade: só pela averbação de conclusão de obra ou habite-se, como estimativa;
sem ela, "Idade não determinável pela matrícula." A primeira compra nunca define a idade.

## Fase D — Possíveis ocupantes

`GET /api/imoveis/{id}/ocupacao/possiveis-ocupantes` lista as pessoas físicas da linha do tempo, com papel, ato, data,
documento e trecho, e o aviso: "Estas pessoas foram identificadas nos documentos do imóvel. Esta informação é apenas uma
sugestão e não confirma ocupação atual."

O registro de ocupação (`OccupancyAnalysis`) ganhou os status `OCUPADO_CONFIRMADO`, `OCUPADO_TERCEIROS` e `NAO_VERIFICADO`
(os anteriores continuam). A verificação (fonte, data, observação, responsável) fica numa `Evidence` vinculada. Os itens 11
e 27 do checklist e o financeiro usam só esse registro; os possíveis ocupantes não respondem nada. Ocupação confirmada sem
custo estimado leva a reserva de desocupação a todos os cenários.

## Fase E — Estimativa condominial pela matrícula

`POST /api/imoveis/{id}/debitos/estimar-condominio/matricula` (`persist=false` calcula; `persist=true` registra numa
`CondominiumEstimate`: baixo → `scenario_otimista`, provável → `scenario_provavel`, alto → `scenario_conservador`).

| Entrada | Ordem |
|---|---|
| Condomínio mensal | informado > mediana dos comparáveis > `condominio.valor_mensal_referencia` (Admin) |
| Aquisição e consolidação | informadas > linha do tempo da matrícula |
| Teto do período | `condominio.periodo_maximo_meses` (60) |
| Cenários | `condominio.fator_cenario_baixo/provavel/alto` (0,15 / 0,35 / 0,70) |
| Encargos | `condominio.multa_pct` (0,02), `condominio.juros_mensal_pct` (0,01), `condominio.correcao_mensal_pct` (0,004) |

Fórmula (visível na resposta e na tela):

```
período = meses entre aquisição e consolidação, limitado ao teto
meses em atraso = período × fator do cenário (arredondado)
principal = mensal × meses
multa = principal × multa
juros = mensal × juros × Σ (meses de atraso de cada cota até hoje)
correção = mensal × correção × Σ (meses de atraso de cada cota até hoje)
total = principal + multa + juros + correção
```

As cotas consideradas são as anteriores à consolidação; a soma dos meses de cada cota até hoje é
`n × meses_desde_consolidação + n × (n + 1) / 2`. O período entre a aquisição e a consolidação **não prova inadimplência**.
A regra da venda é aplicada depois do valor estimado (dívida potencial, parte do comprador, parte do vendedor/Caixa, valor
no financeiro). Na composição de custos, o cenário base usa o provável e o conservador usa o alto. A estimativa deixa o
cálculo do veredito provisório. Aviso obrigatório: "Estimativa calculada com base em informações documentais e premissas
configuráveis. Não representa dívida confirmada. Solicite declaração atualizada ao condomínio."

## Fase F — IPTU dos 4 municípios

Levantamento em 19/11/2026, em páginas públicas oficiais, sem login, sem automação e sem contornar bloqueio:

| Município | Portal | Exige | API | Bloqueio/login | Decisão |
|---|---|---|---|---|---|
| Curitiba/PR | iptu-dam.curitiba.pr.gov.br; cnd-cidadao.curitiba.pr.gov.br | Inscrição + sublote ou indicação fiscal; CPF/CNPJ do proprietário | não | acesso automatizado recusado (HTTP 403) | manual assistida |
| São José dos Pinhais/PR | financas.sjp.pr.gov.br | cadastro imobiliário; usuário e senha | não | login | manual assistida |
| Fazenda Rio Grande/PR | fazendariogrande.pr.gov.br/divisao-de-arrecadacao (Portal do Cidadão Web) | CPF/CNPJ do proprietário | não | dado pessoal | manual assistida |
| Assis/SP | tributacao.assis.sp.gov.br; Via Fácil | cadastro do imóvel | não | verificação de navegador | manual assistida |

Nenhum termo de uso que autorize consulta automatizada foi localizado. Nenhum provider automático foi registrado: a consulta
continua com `ManualAssistedProvider`, e a resposta traz o portal, o identificador, as exigências e o passo a passo
(`municipal_iptu.guidance`; também em `GET /api/imoveis/{id}/debitos/orientacao-iptu`). As fontes ficam em `DebtSource`; a
cobertura de IPTU ainda igual ao seed original passa de `AUTOMATIZAVEL` para `MANUAL` (cobertura editada pelo operador não é
alterada). Testes sem rede.
