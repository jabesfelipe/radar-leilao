# Validação do imóvel 7 — evolução da inteligência (20/11/2026)

Execução **somente leitura** do código da branch `feat/inteligencia-completa` contra os dados de produção do imóvel 7, num
contêiner descartável com `default_transaction_read_only=on` (confirmado `transaction_read_only = on`), removido ao final.
Nenhuma gravação, nenhuma migration, nenhum deploy. Nomes de pessoa física omitidos.

## Imóvel

Apartamento, Fazenda Rio Grande/PR, bairro Estados, 45,50 m² privativos, 2 quartos, 1 vaga, inscrição imobiliária cadastrada.
Documentos: matrícula e condições da venda (analisados). Comparáveis cadastrados: 0.

## Resultado do Resumo

| Item | Resultado | Tipo |
|---|---|---|
| Recomendação | ATENÇÃO — INVESTIGAR | — |
| Lance | R$ 132.970,97 | Fato |
| Valor de venda | desconhecido (amostra insuficiente) | Desconhecido |
| Preço máximo, lucro, ROI, margem | desconhecidos | Desconhecido |
| Investimento total (base) | R$ 145.780,39, com ITBI, débitos, regularização, IPTU e condomínio da posse fora da soma | Estimativa |
| Principal risco | Imóvel ocupado (confirmado pelo cadastro de ocupação) | Fato |
| IPTU | Pendente de consulta; portal oficial da prefeitura; sem automação (consulta pelo CPF/CNPJ do proprietário) | — |
| Condomínio | Estimativa insuficiente (nenhuma referência); dívida acumulada desconhecida, teto conservador R$ 22.000 | Desconhecido |
| Mercado | Venda e aluguel: amostra insuficiente (0); yield não calculado; liquidez indeterminada | — |
| Checklist | P0 em aberto: ação judicial contra o leilão; imóveis parecidos. P1: ocupação, aviso das datas dos leilões, evicção, intimação, reforma | — |
| Documentos | Matrícula e condições da venda analisadas; IPTU, condomínio e laudo/fotos pendentes | — |
| Pesquisa automática | Não configurada (sem `TAVILY_API_KEY`/`BRAVE_SEARCH_API_KEY` em produção) | — |

## Matrícula

- Proprietário atual: CAIXA ECONÔMICA FEDERAL, pela consolidação (Av-5, 15/09/2025).
- Linha do tempo: Abertura, Av-1 (afetação), R-2 (compra e venda), R-3 (alienação fiduciária), Av-4 (conclusão de obra), Av-5
  (consolidação). Protocolos lidos em R-2, R-3 e Av-4. A maior parte das datas fica como "citada": o texto não diz se é de
  protocolo, documento ou registro, e o sistema não deduz.
- Pessoas: credora fiduciária que virou proprietária; adquirente pessoa física que deu o imóvel em garantia e **perdeu o imóvel**
  na consolidação; incorporadora/vendedora (proprietária na abertura, vendedora, fiadora e construtora).

## Problemas achados na validação e corrigidos

1. A data de emissão da certidão era tirada de um "expedido em" de outro documento (26/03/2015). Agora só vale contexto da
   própria certidão. Na revalidação da auditoria do PR #11 (também somente leitura), a data passou a ser lida do campo
   "Data/hora" da própria certidão: 01/10/2025.
2. Rótulo genérico ("INCORPORADORA/CONSTRUTORA") aparecia como pessoa e o nome truncado da construtora aparecia duplicado.
   Agora o rótulo é ignorado e o nome truncado se junta ao completo.
3. Trechos de pesquisa trazem números com espaço ("R$ 1. 800, 00", "45, 50 m²"). O extrator passou a juntar esses números.

## Pesquisa de mercado feita manualmente (referência, não gravada)

Pesquisa pela ferramenta de busca do assistente (não pelo Radar), só para checar a viabilidade da extração. Valores pedidos em
anúncios agregados, sem data de anúncio confiável: **não são dados do imóvel e não foram gravados**.

- Venda, bairro Estados: 45–46 m², 2 quartos, 1 vaga a R$ 193.001; 39 m² a R$ 215.000; 42 m² a R$ 254.400 (condomínio R$ 340)
  ([Viva Real — Rua Manaus](https://www.vivareal.com.br/venda/parana/fazenda-rio-grande/bairros/estados/rua-manaus/apartamento_residencial/),
  [Viva Real — Estados](https://www.vivareal.com.br/venda/parana/fazenda-rio-grande/bairros/estados/apartamento_residencial/)).
  Bairro vizinho Eucaliptos: 45 m², 2 quartos a R$ 199.000 ([ZAP](https://www.zapimoveis.com.br/venda/apartamentos/pr+fazenda-rio-grande++eucaliptos/area-de-servico/)).
- Aluguel na região: R$ 1.800/mês em anúncios de 2 quartos ([Imovelweb](https://www.imovelweb.com.br/imoveis-aluguel-estados-fazenda-rio-grande-drc-rua-para.html)).
- Leitura: 4 referências de venda com datas antigas ou desconhecidas → amostra BAIXA; ordem de grandeza de R$ 4.200 a R$ 6.000/m²
  anunciado. Para o Radar usar esses valores, é preciso configurar o provedor de pesquisa ou cadastrar os anúncios conferidos.

Conteúdo dos anúncios resumido (reescrito por questões de licença).
