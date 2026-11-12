# Contexto de mercado

> Este documento descreve o contexto **qualitativo** em que o Radar opera. Não traz estimativas de mercado, taxas ou valores
> que não estejam sustentados por fonte do repositório. Onde faltar dado, aparece "pendente".

## 1. Leilão extrajudicial de imóveis

O leilão extrajudicial decorre da execução da garantia em contratos com alienação fiduciária (Lei 9.514/97): o credor consolida
a propriedade após a mora do devedor fiduciante e leva o bem a leilão. O Radar trabalha com esse cenário. As regras jurídicas
que ele codifica na Central Jurídica estão em [../02-product/modules/legal.md](../02-product/modules/legal.md) (Lei 9.514 arts. 26, 27 e 37-A;
Código Civil arts. 1.228 e 447; CPC art. 903; Lei 8.245 art. 8º; CTN arts. 130 e 131).

## 2. Por que a análise é difícil (dores que o produto endereça)

Pontos recorrentes que o checklist e as demais áreas tentam cobrir:

- regularidade do procedimento (intimação pessoal ou por edital, notificação dos dois leilões, consolidação registrada);
- situação registral (matrícula, vaga de garagem com matrícula própria, penhoras e indisponibilidades);
- ocupação do imóvel e custo/prazo de desocupação;
- responsabilidade por débitos de IPTU e condomínio, conforme o edital;
- liquidez e comparáveis de mercado para venda e aluguel;
- custos de aquisição, tributos e registro;
- ações judiciais que questionem o leilão.

## 3. O investidor

O modelo mental vem de uma planilha de análise usada pelo proprietário do produto: a navegação do frontend preserva a ideia de
abas por tema (jurídico, financeiro, mercado, ocupação, checklist, riscos, veredito, histórico). O tamanho do mercado, volume
de leilões, deságios típicos e concorrência **não estão documentados no repositório** e, por isso, não são afirmados aqui.

## 4. Fontes de leilão e de dados externos

A revisão de anotações do proprietário lista portais de leilão, serviços de registro eletrônico, notificação (RTD) e desocupação
como **candidatos a avaliação**, não como integrações aprovadas. Regra: sem scraping não autorizado; sem consulta paga sem
autorização, credenciais e limites; enquanto não validado, o fluxo é cadastro ou importação manual. Detalhes em
[../02-product/specs/REVISAO-ANOTACOES-LEILAO.md](../02-product/specs/REVISAO-ANOTACOES-LEILAO.md). Estado real de integrações em
[../03-architecture/integrations.md](../03-architecture/integrations.md).

## 5. Parâmetros jurídico-financeiros em discussão

Os valores abaixo aparecem em anotações como hipóteses e **não estão cadastrados como verdade** no sistema; dependem de fonte
oficial e vigência:

| Tema | Tratamento |
|---|---|
| IR sobre ganho de capital, reinvestimento, redutores por tempo | validação contábil; depende de PF/PJ e regime |
| FUNREJUS, ISSQN, FUNDEP, selo | só com tabela oficial atual, ato, base e vigência |
| Taxa de ocupação (art. 37-A) | validar incidência e jurisprudência |
| "Preço vil" de 50% | critério do leilão judicial; não é piso universal no extrajudicial |
| Usufruto | alerta crítico; óbito alegado não basta, confirmar cancelamento na matrícula |

Estado completo: [evaluation-criteria.md](evaluation-criteria.md).
