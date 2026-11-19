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
