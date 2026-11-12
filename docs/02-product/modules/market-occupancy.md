# Mercado e Ocupação

**Status: implementado** (geocodificação Google opcional; sem integração com portais de anúncios).

## Mercado
- **Objetivo:** avaliar valor de venda e aluguel por comparáveis.
- **Funcionalidades:** comparáveis de venda e aluguel (CRUD com histórico), estatísticas com amostra mínima 7 (`mercado.amostra_minima`) e dispersão alta quando o coeficiente de variação passa de 0,30 (`mercado.cv_dispersao_alta`).
- **Endpoints:** `GET /api/imoveis/{id}/mercado` (router `market.py`), rotas de comparáveis em `main.py`, hub `GET /api/mercado`.
- **Telas:** hub `/mercado`; seção "Mercado" do imóvel.
- **Integração:** Google Geocoding (`geocoding_client.py`), opcional.
- **Limitação:** a coleta de comparáveis é manual; portais de anúncio não estão integrados.

## Ocupação
- **Objetivo:** registrar a situação de ocupação do imóvel e seu histórico, com impacto em financeiro, checklist, riscos e veredito.
- **Funcionalidades:** registro de ocupação com histórico; consultoria e contatos com ocupante no módulo [pós-arrematação](post-auction.md).
- **Endpoints:** `GET/POST /api/imoveis/{id}/ocupacao`, hub `GET /api/ocupacao`.
- **Telas:** hub `/ocupacao`; seção "Ocupação" do imóvel.
- **Regra:** autotutela é proibida (coerção, corte de serviços, entrada forçada); item de checklist de desocupação inclui verificação ética (`ETICA_OCUPACAO`).
- **Observação de arquitetura:** não existe agente de IA separado para ocupação; a situação alimenta os demais domínios.

## Código
`market.py`, `routers/market.py`, `geocoding_client.py`, `main.py`; frontend `pages` e `services` (market, hub).
