# Auditoria mobile — Radar Leilão v1.0.2

Baseline: `main` @ `8894096` (tag `v1.0.2`). **Atualizado após a rodada de correções P0/P1** (branch `homologacao-v1.0.2`,
sem commit/deploy). Situação: **CORRIGIDO** (com teste), **PARCIAL**, **FALHA** (ainda aberta), **NÃO VALIDADO**, **OK**.
Prioridade: **P0** bloqueia a homologação real, **P1** alta, **P2** média, **P3** baixa.

## 1. Como foi medido

- Chrome real (Playwright), frontend em modo dev, **backend real** local (FastAPI + PostgreSQL 16 + pgvector, migrations até `0024`),
  **sem chave OpenAI**, dados 100% fictícios.
- Viewports (7, definidos em `e2e/tests/helpers.ts`): 360×800, 375×812, 390×844, 412×915, 430×932 (celulares), 768×1024 (tablet), 1366×768 (desktop).
  A tabela de "antes × depois" abaixo foi medida na rodada anterior com 5 viewports (375/390/412/768/1280); a rodada com 7 está em §2.1.
- O CSS do produto usa `overflow-x:hidden` em `html`, `body` e `.app-content`, que **esconde** overflow do `scrollWidth`. O teste mede o
  retângulo de cada elemento e só aceita o que estiver dentro de contêiner com rolagem própria.
- Reproduzir: `e2e/README.md`. Evidências (JSON e screenshots) em `e2e/results/` (ignorado pelo Git).

**Limites (não esconder):** Chrome emulando celular não é Safari iOS nem Chrome Android reais; não houve aparelho físico, câmera/galeria,
rede lenta nem teclado virtual. Tabelas administrativas foram medidas com dados reais (município criado + parâmetros), mas as telas
agregadas continuam com poucos dados.

## 2. Resultado antes × depois (mesmas medições, 5 viewports)

| Medida | Antes | Depois |
|---|---|---|
| Rotas com elemento fora da tela | `/oportunidades` (375 e 390) | **0** |
| Seções do imóvel com elemento fora da tela | Histórico (375/390); Central Jurídica e Due Diligence (768) | **0** nas 18 seções, nos 5 viewports |
| Campos com fonte < 16 px (≤ 430 px) | Financeiro 8, Débitos 4, Due Diligence 10, Central Jurídica 2, Wizard 10, Oportunidades 3, Admin 1 | **0** nas telas verificadas |
| Botões/abas com altura < 44 px em telas de toque (≤ 430 px) | 36–40 px | **0** nas seções verificadas |
| Tabelas administrativas sem rolagem | não medido com dados | **0** (5 viewports, dados reais) |

Execução da rodada anterior (5 viewports): **122 testes passaram, 0 falharam, 7 pulados** (IA real, gated).

### 2.1 Rodada com 7 viewports

| Execução | Resultado |
|---|---|
| `correcoes`, `fluxo`, `mobile`, `mobile-detalhe` nos 7 viewports (166 testes; IA real excluída) | **164 passaram, 2 falharam**: Histórico do imóvel em 360×800, elementos até 11 px fora da tela (lista de domínios sem espaços dentro de badge `nowrap`) |
| Correção em `styles.css` (`.history-card .ui-badge` quebra linha; colunas `minmax(0,1fr)` e `min-width:0` no histórico) e reexecução só de `-g "android-360x800"` (6 testes) | **6 passaram, 0 falharam** (duas execuções independentes) |

**Não reexecutado:** a bateria completa de 166 testes depois da correção. O ajuste é restrito ao Histórico, mas os demais viewports não foram remedidos depois dele.

## 3. Matriz

| Funcionalidade | Situação | Evidência | Problema residual | Prio. |
|---|---|---|---|---|
| Login | **OK** | Passou nos 5 viewports | — | — |
| Feedback ao concluir análise | **CORRIGIDO** | Em 390 px, sem chave: título "Análise sem resultado da IA" (alerta vermelho), mensagem, agentes que falharam e avisos; **nunca** "Análise concluída" (`ui-analise-falha-390.png`; E2E; `PropertyDetailPage.test.tsx`) | — | — |
| Reabrir o imóvel após análise falha/parcial | **CORRIGIDO** | Faixa "Última análise (vN): falha/parcial" a partir de `analise_ultima` | — | — |
| Acompanhamento da análise | **PARCIAL** | Se houver análise em andamento (inclusive após recarregar a página), a tela mostra "Análise em processamento" e atualiza sozinha a cada 5 s | A execução continua **síncrona**; sem progresso por agente. Com OpenAI real: **NÃO VALIDADO** (limite do proxy 300 s) | P1 |
| Estado do documento | **CORRIGIDO** | Selo por estado (Indexado / Pronto só texto / OCR necessário / Sem texto / OCR falhou) e lista de etapas com situação e detalhe (`ui-documento-ocr-390.png`) | — | — |
| Upload de documento sem texto | **CORRIGIDO** | O envio é aceito, mas aparece "Documento não pronto para análise" em vermelho; não é apresentado como sucesso pleno | Sem barra de progresso de envio; sem `accept`/`capture` no campo; PDF grande, foto da câmera e rede lenta **NÃO VALIDADO** | P1 |
| Caminhos internos do servidor na tela | **CORRIGIDO** | Removidos da API e da tela | — | — |
| Detalhe — Histórico (375/390) | **CORRIGIDO** | 0 elementos fora da tela; causa raiz: grids sem coluna explícita (`minmax(0,1fr)`) | — | — |
| Detalhe — Central Jurídica (768) | **CORRIGIDO** | Mesma causa | — | — |
| Detalhe — Due Diligence (768) | **CORRIGIDO** | Cartões (`finance-card`) tinham faixa implícita maior que o conteúdo; lista agora em 1 coluna até 980 px | — | — |
| Oportunidades (375/390) | **CORRIGIDO** | Filtros/selects limitados ao cartão | — | — |
| Fonte dos campos (zoom do iOS) | **CORRIGIDO** | 16 px em telas ≤ 680 px ou de toque; medido nas telas listadas | Telas não visitadas pelo teste podem ter campos próprios | — |
| Alvos de toque | **CORRIGIDO** (botões e abas) / **PARCIAL** (links e ícones) | Altura mínima de 44 px em `ui-button`, abas do imóvel e da administração | Links soltos e botões-ícone não medidos | P2 |
| Tabelas da Administração | **CORRIGIDO** | Rolagem horizontal dentro da tabela em ≤ 980 px; medido com dados reais nos 5 viewports | — | — |
| Texto da Administração ("token… até a frente de autenticação") | **FALHA** (aberta) | Não alterado nesta rodada | Texto desatualizado desde o login/JWT; escrita admin **NÃO VALIDADA** | P1 |
| Navegação por seções do imóvel | **PARCIAL** | 18 abas alcançáveis; seção ativa fora da URL | "Voltar" do celular sai do imóvel | P2 |
| Menu lateral (drawer) | **PARCIAL** | Funciona; título da topbar trunca em ≤ 412 px; sem `role=dialog`/Esc/trap de foco (**só leitura de código**) | Acessibilidade | P2 |
| Nova versão de documento pela UI | **FALHA** (aberta) | Rota existe, **sem botão**; o reenvio do mesmo arquivo agora reprocessa quando a versão anterior não estava pronta | — | P2 |
| Aviso de segurança (`SecurityNotice`), diálogos `prompt`/`confirm`, erro 422 genérico | **FALHA** (aberta) | Não alterados | — | P2/P3 |
| Cadastro completo pelo wizard (preencher e salvar na UI) | **NÃO VALIDADO** | O wizard abre sem overflow e com fontes corretas; o preenchimento completo e o salvamento pela UI não foram executados em navegador (cadastro feito por API) | — | P1 |
| Navegador real em iOS/Android | **NÃO VALIDADO** | Só Chrome emulado | Safari, teclado virtual e `viewport-fit` | **P0** |
| Acesso em produção (HTTP) | **PARCIAL** | `REQUIRE_HTTPS` recusa a API em HTTP (testado); o TLS no proxy é ação do operador | Ver PLANO §5 | **P0** |

## 4. Bloqueadores restantes para homologar o imóvel real pelo celular

1. Teste em iPhone e Android **reais** (P0).
2. HTTPS no proxy + `REQUIRE_HTTPS=true` antes de enviar documento com dados pessoais (P0, ação de infraestrutura).
3. Cadastro completo pelo wizard validado em navegador (P1).
4. Texto desatualizado da Administração e escrita admin (P1).

## 5. Arquivos de CSS/UI alterados

`frontend/src/styles.css` (bloco final "Correções de layout mobile/tablet"), `DocumentsSection.tsx`, `PropertyDetailPage.tsx`,
`HistorySection.tsx`, serviços `analysisStatus.ts`, `documents.ts`, `history.ts`, `properties.ts`.
