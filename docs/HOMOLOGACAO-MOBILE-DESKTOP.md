# Homologação mobile e desktop

Data: 2026-11-14. Código: `main` depois do merge da v1.0.4 (`281b554`, `e5967b2`), mais o ajuste de CSS descrito abaixo.

## Ambiente

| Item | Valor |
|---|---|
| Backend | local (WSL), `uvicorn` em `0.0.0.0:8100`, banco PostgreSQL de teste `radar_hom` recriado do zero, migrations até `0025` |
| Chave OpenAI | **não configurada** (testes sem custo; os fluxos de IA devem informar "IA indisponível") |
| Frontend | Vite dev server em `127.0.0.1:5180`, `VITE_API_URL=http://127.0.0.1:8100` |
| Navegador | Google Chrome (canal `chrome` do Playwright), headless, 1 worker |
| Dados | só fictícios (`HOM-FICTICIO …`, matrícula fictícia, CPF `000.000.000-00`) |

## Validação de código

| Verificação | Resultado |
|---|---|
| Backend `pytest` (suite completa, banco novo) | 1205 passed, 3 skipped |
| Frontend `tsc -b` | 0 erros |
| Frontend `vitest` | 29 arquivos, 182 testes passaram |
| Frontend `vite build` | OK (JS 459 kB, gzip 118 kB) |
| GitHub Actions CI no push da `main` (`e5967b2`, run #34) | success |

## E2E Playwright

Specs: `correcoes.spec.ts`, `fluxo.spec.ts`, `mobile.spec.ts`, `mobile-detalhe.spec.ts`. Viewports: 360x800, 390x844, 412x915, 1366x768, 1920x1080 (o 1920x1080 foi adicionado em `e2e/tests/helpers.ts`).

Comando:

```bash
cd e2e
npx playwright test mobile.spec.ts mobile-detalhe.spec.ts correcoes.spec.ts fluxo.spec.ts \
  -g "360x800|390x844|412x915|1366x768|1920x1080|P0|fluxo sem chave"
```

Resultado: **122 testes, 122 passaram** (4,0 min).

O que é verificado em cada viewport:

- login pela interface;
- as 14 rotas do menu e o detalhe do imóvel, sem elemento fora da tela e sem tabela larga sem rolagem própria;
- inputs com fonte de pelo menos 16px nos celulares (evita zoom automático no iOS);
- as 18 seções do detalhe do imóvel, alcançáveis e sem estouro horizontal;
- wizard de cadastro;
- administração (abas e tabelas);
- fluxo sem chave: cadastro, upload, processamento, análise transparente sobre a ausência de IA, registro de uso em `llm_runs`, upload e análise pela interface a 390px.

### Medições agregadas (rotas do menu + detalhe, 16 telas por viewport)

| Viewport | Fora da tela | Tabela sem rolagem | Input < 16px | Alvo de toque < 44px | Texto cortado |
|---|---|---|---|---|---|
| 360x800 | 0 | 0 | 0 | 2 | 16 |
| 390x844 | 0 | 0 | 0 | 2 | 15 |
| 412x915 | 0 | 0 | 0 | 2 | 15 |
| 1366x768 | 0 | 0 | não se aplica | não se aplica (mouse) | 0 |
| 1920x1080 | 0 | 0 | não se aplica | não se aplica (mouse) | 0 |

## Problemas encontrados e correção

1. **Título da topbar espremido no celular.** Em todas as telas a 360/390/412px, o nome e o perfil do usuário ocupavam a largura da topbar: o "RADAR LEILÃO" quebrava em duas linhas cortadas e o título "Central de análise patrimonial" virava "C…". Era a origem de todos os itens "texto cortado" da tabela.
   Correção em `frontend/src/styles.css`: até 680px, o bloco com nome e perfil (`.topbar-user-meta`) fica oculto. O selo com as iniciais continua visível, e o `title` dele ainda mostra o e-mail e o perfil.
2. **Filtros de Oportunidades com 37px de altura no celular** (selects de modalidade e fase), abaixo dos 44px recomendados para toque.
   Correção: até 680px, `.opp-filters select` tem `min-height: 44px`.

No desktop, os botões "Sair" (36px) e as abas da administração (39px) ficam abaixo de 44px. Isso não é problema para uso com mouse e não foi alterado.

Reexecução depois da correção: ver a seção abaixo.

### Reexecução após a correção

Specs `mobile.spec.ts`, `mobile-detalhe.spec.ts` e `correcoes.spec.ts` nos três celulares (`-g "360x800|390x844|412x915"`): **66 testes, 66 passaram** (2,4 min). Depois da correção, o frontend continua com `tsc` 0 erros, 182 testes `vitest` e build OK.

| Viewport | Fora da tela | Tabela sem rolagem | Input < 16px | Alvo de toque < 44px | Texto cortado |
|---|---|---|---|---|---|
| 360x800 | 0 | 0 | 0 | 0 (antes 2) | só o título da topbar, com reticências intencionais |
| 390x844 | 0 | 0 | 0 | 0 (antes 2) | idem |
| 412x915 | 0 | 0 | 0 | 0 (antes 2) | idem |

O título ainda conta como "cortado" porque usa `text-overflow: ellipsis` de propósito. A 360px aparece "Central de análise …" em uma linha, com "RADAR LEILÃO" inteiro acima. As capturas ficam em `e2e/results/mobile/` (não versionado).

## Como testar num celular físico

Situação medida nesta máquina (`ipconfig`, 2026-11-14):

- IPv4 da Wi-Fi: `192.168.15.81` (máscara 255.255.255.0, gateway 192.168.15.1). O endereço vem do DHCP e pode mudar; confira com `ipconfig` antes de testar.
- O backend roda dentro do WSL2 em modo NAT (sem `.wslconfig`; IP interno do WSL `172.28.181.113`, que também muda a cada reinício). Por isso o celular **não alcança a porta 8100 diretamente**. O Windows só repassa `localhost` para o WSL.

Nada abaixo foi aplicado. Os passos 3 e 4 mudam a rede e o firewall do Windows e precisam de autorização sua (e de um terminal como administrador).

1. Celular e computador na **mesma rede Wi-Fi**. Não use rede de convidados (costuma isolar os aparelhos).
2. Suba o backend com o CORS liberando a origem do celular. No `hom_up.sh` (ou no `.env` local), use:
   `CORS_ALLOW_ORIGINS=http://localhost:5180,http://127.0.0.1:5180,http://192.168.15.81:5180`
3. Repasse a porta 8100 do Windows para o WSL (PowerShell como administrador):
   ```powershell
   $wsl = (wsl -d Ubuntu -- hostname -I).Split(' ')[0]
   netsh interface portproxy add v4tov4 listenaddress=192.168.15.81 listenport=8100 connectaddress=$wsl connectport=8100
   ```
4. Libere as portas 5180 e 8100 só para a rede local e só no perfil "Privada":
   ```powershell
   New-NetFirewallRule -DisplayName "Radar hom 5180" -Direction Inbound -Protocol TCP -LocalPort 5180 -Profile Private -RemoteAddress LocalSubnet -Action Allow
   New-NetFirewallRule -DisplayName "Radar hom 8100" -Direction Inbound -Protocol TCP -LocalPort 8100 -Profile Private -RemoteAddress LocalSubnet -Action Allow
   ```
   Confira se a Wi-Fi está como rede "Privada" nas configurações do Windows.
5. Suba o frontend escutando na rede e apontando a API para o IP do computador:
   ```bat
   cd frontend
   set VITE_API_URL=http://192.168.15.81:8100
   npx vite --host 0.0.0.0 --port 5180 --strictPort
   ```
6. No celular, abra `http://192.168.15.81:5180` e entre com o usuário de homologação (`hom@local.test`). Roteiro sugerido:
   - login;
   - abrir o menu e navegar até "Administração" (último item);
   - Oportunidades com os filtros;
   - detalhe do imóvel, rolando a barra de seções até a última;
   - wizard de cadastro (verificar se o teclado não dá zoom);
   - upload de um documento fictício;
   - girar o aparelho (retrato e paisagem).
7. Ao terminar, desfaça a exposição:
   ```powershell
   netsh interface portproxy delete v4tov4 listenaddress=192.168.15.81 listenport=8100
   Remove-NetFirewallRule -DisplayName "Radar hom 5180"
   Remove-NetFirewallRule -DisplayName "Radar hom 8100"
   ```

Cuidados:

- é HTTP sem criptografia; use só dados fictícios e só na rede de casa;
- não use a chave OpenAI nesse ambiente exposto;
- não faça isso numa rede corporativa ou pública.

Alternativa sem mexer no firewall: testar na VPS de homologação, depois que o HTTPS estiver configurado (ver `docs/06-quality/homologacao-v1.0.4/PLANO-HTTPS-VPS.md`).
