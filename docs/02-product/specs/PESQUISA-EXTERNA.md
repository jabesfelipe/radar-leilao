# SPEC — Pesquisa externa autorizada (v1.0.14)

Status: implementado na branch `feat/inteligencia-completa` (não publicado). Migration `0027_pesquisa_externa`.

## 1. Objetivo

O Radar pesquisa sozinho anúncios de venda e aluguel, valores de condomínio e o portal do IPTU antes de pedir dado ao usuário,
usando só APIs de pesquisa contratadas. Nada é inventado: sem provedor configurado, a tela diz "não configurado" e o que configurar.

## 2. Avaliação de provedores (nov/2026)

| Provedor | Custo | Fontes e formato | Limites / termos | Decisão |
|---|---|---|---|---|
| [Tavily](https://docs.tavily.com/documentation/api-credits) | 1.000 créditos grátis/mês; depois US$ 0,008 por crédito (busca básica = 1 crédito) | URL, título, conteúdo relevante da página, data | API feita para uso automatizado; chave por conta | **Principal** |
| [Brave Search API](https://brave.com/search/api/) | US$ 5 por 1.000 consultas, com US$ 5 de crédito mensal | URL, título, descrição, trechos extras, idade da página | Índice próprio; uso por API permitido | **Alternativo** |
| [Google Custom Search JSON API](https://developers.google.com/custom-search/v1/overview) | — | — | Fechada a novos clientes; encerra em 01/01/2027 | Descartado |
| APIs que raspam o Google (ex.: SerpAPI) | variável | — | Risco de termos de uso do Google | Descartado |
| Portais de anúncio (ZAP, Viva Real, OLX, Imovelweb) | — | — | Termos proíbem coleta automatizada; sem API pública | **Não acessados**: o Radar lê só o que a API de pesquisa devolve |

Conteúdo da tabela resumido das páginas citadas (reescrito por questões de licença).

## 3. Arquitetura

- `backend/app/search/providers.py`: `TavilyProvider`, `BraveProvider` (contrato `SearchProvider`: `configured`, `search`). Erros:
  `SearchUnavailable` (timeout, transporte, 429, 5xx: tenta de novo e passa ao alternativo) e `SearchError` (4xx: passa ao alternativo).
- `backend/app/search/service.py`: cadeia principal → alternativo, retry (`SEARCH_MAX_RETRIES`) com espera crescente
  (`SEARCH_RETRY_BACKOFF_SECONDS`) em 429/5xx/timeout, timeout, cache por (imóvel + tipo + consulta normalizada + domínios) por
  `SEARCH_CACHE_HOURS` (imóveis diferentes não compartilham registro), registro em `external_searches` (status, provedor,
  duração, tentativas, custo estimado, erro, resultados, validade). A chave nunca é registrada nem devolvida.
- `POST /api/imoveis/{id}/pesquisa-automatica` é operação crítica no portão de segurança: exige `analysis:write` e usa o
  limite por minuto e de concorrência das operações que consomem serviço externo.
- `backend/app/search/extract.py`: lê preço, área, quartos, vagas, condomínio, IPTU e menção a taxa extra do título/trecho
  devolvido; descarta página de listagem (vários preços), texto sem preço e tipo errado; marca duplicatas (mesma URL ou mesmo
  preço + área). Valor ausente fica ausente.
- `backend/app/market_research.py`: monta as consultas do imóvel (nome do condomínio/empreendimento quando o cadastro traz,
  tipo, quartos, bairro, cidade), grava os anúncios utilizáveis como `MarketComparable` (`price_type=ANUNCIADO`, fonte, URL,
  data da coleta, confiança nas observações) e devolve o que foi descartado e por quê. Roda na análise do imóvel quando há
  provedor (`SEARCH_AUTO_ON_ANALYSIS`) e sob demanda (`POST /api/imoveis/{id}/pesquisa-automatica`).

Os comparáveis pesquisados entram no mesmo cálculo dos manuais: mercado (similaridade, discrepantes, desconto de negociação),
taxa de condomínio do Financeiro (mínimo de 3 referências), cenários e preço máximo.

## 4. Configuração

| Variável | Padrão | Uso |
|---|---|---|
| `SEARCH_ENABLED` | `true` | Liga/desliga toda pesquisa externa |
| `SEARCH_PROVIDER_PRIMARY` / `SEARCH_PROVIDER_FALLBACK` | `tavily` / `brave` | Ordem dos provedores (`""` desativa) |
| `TAVILY_API_KEY` | vazio | Chave Tavily (https://app.tavily.com) |
| `BRAVE_SEARCH_API_KEY` | vazio | Chave Brave (https://api-dashboard.search.brave.com) |
| `SEARCH_TIMEOUT_SECONDS` | `20` | Timeout por chamada |
| `SEARCH_MAX_RETRIES` | `1` | Novas tentativas em falha transitória |
| `SEARCH_CACHE_HOURS` | `168` | Validade do cache (custo) |
| `SEARCH_MAX_QUERIES_PER_RUN` | `8` | Limite de consultas por execução |
| `SEARCH_AUTO_ON_ANALYSIS` | `true` | Pesquisa ao analisar o imóvel |

As variáveis entram no `.env` do servidor (repassadas pelo `docker-compose.yml`). Nunca no repositório nem no frontend.

## 5. Rotas

- `GET /api/pesquisa/provedores`: provedores configurados (sem chave).
- `GET /api/imoveis/{id}/pesquisa-automatica`: histórico das consultas do imóvel.
- `POST /api/imoveis/{id}/pesquisa-automatica` (`{"tipos": ["VENDA","ALUGUEL","CONDOMINIO","IPTU_PORTAL"]}`): pesquisa um imóvel.

## 6. Limitações

- O trecho devolvido pela API nem sempre traz preço e área; anúncios sem esses dados não viram comparável.
- Preço de anúncio não é transação: amostra só de pesquisa automática é limitada a MÉDIA no Resumo.
- Portal de IPTU encontrado por pesquisa aparece como "confirme se é o oficial"; a consulta continua assistida.
