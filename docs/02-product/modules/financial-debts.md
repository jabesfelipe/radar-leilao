# Financeiro e Central de Débitos

**Status: implementado** (cenário BASE do veredito, cenários conservador/base/otimista da inteligência de mercado e cenários do usuário; TIR/VPL e sensibilidade planejados). Consulta de débitos: provider manual-assistido.

## Objetivo
Calcular custo total, resultado, margem, ROI e preço máximo do lance, e consolidar débitos e despesas do imóvel.

## Funcionalidades
- **Composição única** (consistência financeira v2): custo total, resultado, ROI, break-even e preço máximo do veredito
  (`services.build_finance` → `viability.verdict_finance`) vêm da mesma composição de custos e do mesmo cenário BASE da
  inteligência de mercado. Para as mesmas premissas, os dois apresentam os mesmos números. Regras em
  [evaluation-criteria.md](../../01-business/evaluation-criteria.md#4-análise-financeira).
- ITBI pela alíquota informada (base: maior entre aquisição e base mínima) quando não há custo cadastrado; sem alíquota ou base, fica pendente e fora da soma.
- Corretagem e IR não informados usam o padrão declarado (6% e 15% sobre o ganho), sinalizado, e o cálculo fica provisório; nunca zero.
- Cada item da composição tem natureza (confirmado, premissa do usuário, estimado, pendente com reserva, pendente fora da soma, não aplicável) e origem; a tela mostra a tabela "Composição dos custos".
- Preço máximo pela meta do usuário (LUCRO_MINIMO, MARGEM_MINIMA, ROI_MINIMO), igual no veredito e na inteligência de mercado; sem meta, o veredito não calcula preço máximo.
- Cenários do usuário (`cenarios` nas premissas) calculados com a mesma composição; os valores informados substituem só os itens correspondentes.
- Sugestões de premissas a partir da inteligência de mercado (valor de venda, corretagem, IR, prazo, carregamento), aplicadas só no clique; a meta nunca é sugerida.
- Motor legado `finance.py` (`calculate_financial`): mantido para campos legados (deságio, aluguel/yield, detalhe da comissão) e para os testes de lógica do veredito.
- Premissas financeiras editáveis; o formulário preserva as premissas da v1.0.8 ao salvar; análises financeiras versionadas (V1 a V9 no imóvel de referência).
- Custos do imóvel (CRUD com histórico).
- Central de Débitos: débitos normalizados, consolidação por natureza (confirmados, informados, estimados, despesas previstas), estimativa condominial com 3 cenários (sempre ESTIMADO), histórico de consultas de débito.
- Catálogos administráveis: municípios, tipos de débito, fontes e matriz de cobertura (ver [administration.md](administration.md)).

## Telas
Hub `/financeiro`; no imóvel: "Financeiro" e "Débitos".

## Endpoints
`GET /api/imoveis/{id}/financeiro`, `GET/PUT .../financeiro/premissas`, `POST .../financeiro/analisar`; `GET/POST/PATCH/DELETE /api/imoveis/{id}/custos`; débitos: `GET/POST /api/imoveis/{id}/debitos`, `GET/PATCH .../{debt_id}`, `GET .../consolidacao`, `GET .../consultas`, `POST .../consultar`, `GET .../estimativas-condominio`, `POST .../estimar-condominio`; hub `GET /api/financeiro`.

## Integrações
`debt_providers.py`: apenas manual-assistido. Sem integração automática com prefeituras ou administradoras.

## Limitações e divergências
- Categorias de custo fixas; sem parametrização fiscal por jurisdição, ato e vigência ([MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS](../specs/MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS.md)).
- Sem TIR, VPL, fluxo descontado nem grid de sensibilidade.
- IR conservador: dívidas em atraso, desocupação, certidões, regularização e condomínio/IPTU da posse não reduzem a base do ganho de capital; isenções e redutores por tempo de posse não são aplicados.
- O cálculo do veredito consulta a inteligência de mercado a cada leitura do financeiro (estimativa e busca do preço máximo); a suíte de testes ficou ~20 s mais lenta.
- Comentário em `backend/app/models.py` cita o plano antigo `PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN` (ver [99-archive](../../99-archive/README.md)).

## Código
`viability.py` (composição única, `verdict_finance`), `services.py` (`build_finance`, `harmonize_finance`), `finance.py`, `estimates_service.py`, `debts_service.py`, `debt_providers.py`, `debt_query_service.py`, `routers/debts.py`, `impact.py`; frontend `FinancialSection.tsx`, `PremisesSuggestions.tsx`, `CostComposition.tsx`.
