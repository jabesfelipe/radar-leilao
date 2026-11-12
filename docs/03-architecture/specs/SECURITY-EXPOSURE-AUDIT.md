# Radar Leilão — Auditoria de exposição remota (pré-Contabo)

Revisão feita lendo o código (`backend/app/main.py`, `backend/app/routers/*.py`,
`auth.py`, `authz.py`) e testando o proxy de produção numa simulação local. Nenhuma regra de
negócio foi alterada.

## 1. Como a autenticação funciona hoje

- **JWT** (`auth.py`): `get_current_user` exige `Authorization: Bearer`; segredo
  `JWT_SECRET_KEY` (sem ele: 503, falha fechada); expiração 480 min.
- **RBAC** (`authz.py`): `require_permission(perm)` aceita JWT **ou** o legado
  `X-Admin-Token`. O compose de produção **não repassa** `ADMIN_API_TOKEN`/`AUTHZ_ROLE_TOKENS`,
  então na VPS só o JWT vale.
- **Não há dependência global**: `FastAPI()` sem `dependencies=`, routers sem
  `dependencies=`, sem middleware de auth (só CORS). Cada rota decide sozinha.
- **Sem escopo por dono**: um JWT válido de qualquer papel enxerga todos os imóveis.
- O frontend já injeta o Bearer em **toda** chamada `/api` (`frontend/src/services/session.ts`),
  então fechar as rotas legadas no backend não exige mudar os serviços do frontend.

Totais: **184 rotas**; **36 exigem credencial** (21 só JWT + 15 RBAC); **148 não exigem**
(112 em `main.py` + 36 em routers). `POST /api/auth/login` e `GET /health` são públicas por
desenho.

## 2. Rotas SEM JWT (relação completa)

`IMV` = `/api/imoveis/{property_id}`. “Escreve” = altera banco; “LLM” = pode acionar
provedor pago se houver chave; “Arquivo” = recebe arquivo.

### 2.1 `/api/imoveis/...` (main.py)

| Método | Caminho | Dados acessíveis / efeito |
|---|---|---|
| GET | /api/imoveis | lista de todos os imóveis (cadastro completo) |
| POST | /api/imoveis | **escreve**: cria imóvel |
| POST | /api/imoveis/completo | **escreve**: imóvel + leilão + edital + matrícula + fontes |
| GET | IMV | dossiê inteiro: imóvel, leilão, edital, matrícula, fontes, documentos (com `normalized_path`), evidências, processos, custos, dívidas, comparáveis, checklist, riscos, análises, eventos, veredito, jurídico, financeiro |
| PATCH | IMV | **escreve**: dados cadastrais |
| GET/POST | IMV/fontes | fontes do imóvel / **escreve** |
| GET | IMV/fontes/historico | histórico de fontes |
| PATCH/DELETE | IMV/fontes/{source_id} | **escreve/apaga** fonte |
| GET | IMV/checklist, IMV/checklist/historico | checklist do imóvel e histórico |
| PATCH | IMV/checklist/{item_id} | **escreve**: resposta de item |
| GET | IMV/financeiro, IMV/financeiro/premissas | análise financeira e premissas |
| PUT | IMV/financeiro/premissas | **escreve** premissas |
| POST | IMV/financeiro/analisar | **escreve**: recalcula análise financeira |
| GET/POST | IMV/ocupacao | ocupação / **escreve** |
| GET/POST | IMV/matricula; PATCH IMV/matricula/{registration_id} | matrícula (titular, cartório) / **escreve** |
| GET/POST | IMV/edital; PATCH IMV/edital/{notice_id} | edital / **escreve** |
| POST | IMV/documentos | **Arquivo**: upload (entra no pipeline OCR/RAG); resposta traz `original_path`/`normalized_path`/`extraction_metadata` |
| GET | IMV/documentos | documentos e versões com caminhos internos de storage |
| POST | IMV/documentos/{document_version_id}/extrair | **LLM**: extração |
| GET | IMV/documentos/{document_version_id}/extracao | resultado da extração |
| POST | IMV/analises/{analysis_id}/agents/documental · juridico · financeiro · mercado · checklist | **LLM** (5 rotas) |
| POST | IMV/analisar | **LLM/escreve**: análise completa (nova versão) |
| POST | IMV/eventos/{event_id}/reanalisar | **LLM/escreve**: reanálise incremental |
| GET | IMV/historico | histórico de análises |
| POST | IMV/leilao; PATCH IMV/leilao/{auction_id} | **escreve** leilão |
| POST | IMV/leilao/leiloeiro | **escreve** vínculo com leiloeiro |
| GET/POST | IMV/custos; PATCH/DELETE IMV/custos/{cost_id} | custos / **escreve/apaga** |
| GET/POST | IMV/dividas; PATCH/DELETE IMV/dividas/{debt_id} | dívidas / **escreve/apaga** |
| GET/POST | IMV/comparaveis; PATCH/DELETE IMV/comparaveis/{comparable_id} | comparáveis / **escreve/apaga** |
| GET/POST | IMV/processos; PATCH IMV/processos/{process_id} | processos judiciais (partes) / **escreve** |
| POST | IMV/processos/{process_id}/movimentacoes | **escreve** |
| POST | IMV/processos/consultar | consulta externa (DataJud) |
| POST | IMV/juridico/processos/{process_id}/vincular | **escreve** |
| GET | IMV/juridico/riscos, IMV/juridico/evidencias | riscos e evidências jurídicas |
| GET/POST | IMV/evidencias; GET IMV/evidencias/{evidence_id} | evidências (com trecho do documento) / **escreve** |
| POST | IMV/evidencias/{evidence_id}/links | **escreve** |
| GET | IMV/pos-arrematacao | pós-arrematação completo |
| POST | IMV/pos-arrematacao/ativar | **escreve** |
| PATCH | IMV/pos-arrematacao | **escreve** |
| POST/PATCH/DELETE | IMV/pos-arrematacao/etapas[/{stage_id}] | **escreve/apaga** |
| POST/PATCH/DELETE | IMV/pos-arrematacao/custos[/{cost_id}] | **escreve/apaga** |
| POST/PATCH/DELETE | IMV/pos-arrematacao/contatos[/{contact_id}] | contatos (nome/telefone de ocupantes) / **escreve/apaga** |
| POST | IMV/pos-arrematacao/contatos/{contact_id}/tentativas | **escreve** |
| POST/PATCH/DELETE | IMV/pos-arrematacao/consultorias[/{consultancy_id}] | **escreve/apaga** |
| POST | IMV/pos-arrematacao/consultorias/{consultancy_id}/propostas | **escreve** |
| POST | IMV/pos-arrematacao/notificacoes | **escreve** rascunho |
| GET/PATCH | IMV/pos-arrematacao/notificacoes/{draft_id} | rascunho de notificação / **escreve** |
| POST | IMV/pos-arrematacao/notificacoes/{draft_id}/versoes | **escreve** |
| GET | IMV/due-diligence | due diligence |
| GET/PUT | IMV/localizacao | localização / **escreve** |
| POST | IMV/localizacao/geocodificar | chamada externa (Google, se houver chave) |
| POST | IMV/due-diligence/prefeitura/debito | **escreve** |
| POST | IMV/due-diligence/{frente}/revisar | **escreve** |
| GET | IMV/debitos, IMV/debitos/consolidacao, IMV/debitos/consultas, IMV/debitos/estimativas-condominio, IMV/debitos/{debt_id} | débitos (routers/debts.py) |
| POST | IMV/debitos, IMV/debitos/consultar, IMV/debitos/estimar-condominio | **escreve** / consulta provedor |
| PATCH | IMV/debitos/{debt_id} | **escreve** |
| GET | IMV/juridico/central | central jurídica do imóvel |
| GET | IMV/mercado | dados de mercado |

### 2.2 Outras rotas sem JWT

| Método | Caminho | Dados / efeito |
|---|---|---|
| POST | /api/documentos/{document_id}/versoes | **Arquivo**: nova versão de documento |
| GET/POST/PATCH/… | /api/checklist, /api/checklist/{item_id}, …/ativar, …/desativar, …/historico | catálogo mestre do checklist / **escreve** |
| GET/POST | /api/leiloeiros; GET/PATCH/DELETE /api/leiloeiros/{id}; GET …/historico | leiloeiros (contato) / **escreve/apaga** |
| POST/PATCH/DELETE | /api/leiloeiros/{id}/portais[/{portal_id}] | acessos a portais (usuário; senha cifrada) / **escreve/apaga** |
| GET | /api/leiloeiros/{id}/portais/{portal_id}/credencial | **senha decifrada**; exige só `X-Portal-Admin-Token`. Na VPS o token não é repassado ⇒ **503 (fechada)** |
| POST/PATCH/DELETE | /api/leiloeiros/{id}/documentos[/{document_id}] | metadados de documentos do leiloeiro / **escreve/apaga** |
| GET | /api/dashboard, /api/imoveis-resumo, /api/financeiro, /api/juridico, /api/riscos, /api/veredito, /api/mercado, /api/ocupacao, /api/documentos, /api/historico, /api/checklist-global | hubs agregados de todos os imóveis |
| GET | /api/juridico/biblioteca, …/busca, /api/juridico/referencias/checklist/{key}, …/contexto/{ctx} | biblioteca jurídica |
| GET | /api/admin/municipios, /api/admin/tipos-debito | catálogos (**semeiam dados na leitura**) |
| GET | /api/admin/fontes, /api/admin/parametros, …/categorias, …/resolver, …/{id}/historico, /api/admin/cobertura | parâmetros de negócio e cobertura |
| POST | /api/auth/login | público por desenho (rate limit no proxy) |
| GET | /health | público (só status) |

### 2.3 Rotas que exigem credencial (36)

- **JWT** (21): `/api/auth/me`; `/api/dashboard/oportunidades`; `/api/documentos/versoes/{id}/arquivo`
  (download); `/api/monitoring/readiness|rag|rag/pending`; todo `/api/oportunidades/...`
  (escritas exigem também `analysis:write`).
- **RBAC** (15): `/api/auth/usuarios` (GET/POST/PATCH, `user:manage`); escritas de
  `/api/admin/*` (`admin:write`/`admin:parameters`); `/api/monitoring/storage`;
  `POST /api/monitoring/rag/reprocess`.

### 2.4 Outras exposições

- `GET IMV/documentos` e `GET IMV` devolvem `original_path`/`normalized_path` (caminho
  interno no storage). Não é baixável por URL (não há arquivo estático servido), mas revela
  a estrutura interna.
- `/docs`, `/redoc`, `/openapi.json` existem no backend (padrão FastAPI) e são bloqueados no
  proxy (404).
- `judicial_api/` (serviço separado) fica sem auth em modo local; **não** faz parte do
  compose de produção.

## 3. Portão do proxy: o que foi testado

Ver evidência em §5. Toda rota que chega ao backend ou ao frontend passa por
`if ($gate_ok = 0) { return 403; }`. As únicas exceções são `/_proxy_health` (texto fixo
`ok`), `/acesso` (só entrega o cookie com a chave correta) e `/docs|/redoc|/openapi.json`
(404 fixo, sem upstream). Caminhos alternativos (`//api`, `/x/../api`, `%61pi`, `%2F`,
`/docs/../api`, `/_proxy_health/../api`, maiúsculas), métodos (POST/DELETE/OPTIONS/HEAD),
Host forjado, HTTP/1.0, cookie errado/prefixo/sufixo, chave em query/header,
`X-Admin-Token`, upload, download, `/api/admin`, `/api/auth/usuarios` e arquivos estáticos
do frontend: todos **403** sem o cookie.

Correções feitas nesta revisão:
- **`map_hash_bucket_size`**: com `GATE_KEY` de 48 caracteres (`openssl rand -hex 24`, como
  documentado) o nginx **não subia** (`could not build map_hash`). Corrigido (256).
- **`/acesso` fora dos logs**: a URL contém a chave; `access_log off` + `error_log /dev/null`
  na location e `Cache-Control: no-store`. Não há rate limit em `/acesso` (o `return` roda
  antes da fase de limite do nginx); a defesa é a entropia: o `deploy.sh` exige ≥ 48 hex
  (192 bits).
- **Proxy reiniciado no deploy**: o template é montado como arquivo; sem `restart` o nginx
  seguia com a config antiga após um `update`.
- `GET /api` (sem barra) responde 301 para `/api/` sem cookie: redirecionamento automático
  do nginx, sem dados; o destino exige o cookie.
- Headers de segurança repetidos em `/acesso` (o `add_header` local anulava os do server).

## 4. Riscos residuais e decisão

| # | Risco | Mitigação atual | Classificação |
|---|---|---|---|
| R1 | 148 rotas sem JWT (inclui escrita, upload e LLM) | portão do proxy + rede privada | **Bloqueador para acesso público ou usuários não confiáveis**; aceitável na homologação privada com poucas pessoas de confiança |
| R2 | Quem tem o cookie do portão ignora o RBAC nessas rotas (um CONSULTA consegue escrever) | homologadores de confiança | IMPORTANTE |
| R3 | HTTP em texto claro (modo A) expõe senha, JWT, cookie e documentos | modo B (WireGuard + HTTPS `*.ts.net`) é o padrão | Bloqueador **só** no modo A |
| R4 | JWT em `localStorage` (XSS o leria) | CSP inexistente; app sem conteúdo de terceiros | DESEJÁVEL (CSP) |
| R5 | `PORTAL_SECRET_KEY` não repassado ⇒ cadastro de senha de portal falha fechado na VPS | intencional nesta fase | PÓS-HOMOLOGAÇÃO |

Correção definitiva de R1/R2 (próxima missão, fora do escopo “sem novas funcionalidades”):
dependência `get_current_user` no nível do app para `/api/*` (exceto login/health) +
`require_permission` nas escritas, com os testes legados passando a autenticar.

## 5. Evidência (simulação local, 2026-11)

Executada com o compose de produção (`radar-prod`, volumes de teste), `GATE_KEY` de 48 hex,
proxy em `127.0.0.1:8088`. Resultados em `docs/PROJECT-STATUS.md` (bloco do topo).
