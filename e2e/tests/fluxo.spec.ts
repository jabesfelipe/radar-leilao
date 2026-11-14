import { test, expect } from '@playwright/test'
import { appendFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { API_URL, MATRICULA_FICTICIA, apiLogin, auth, criarImovelFicticio, injetarSessao, type Sessao } from './helpers'

/**
 * Fluxo cadastro -> upload -> processamento -> analise -> visualizacao mobile.
 * Roda contra backend REAL local (PostgreSQL + pgvector) SEM chave OpenAI.
 * Este arquivo NAO comprova integracao com a OpenAI (ver ia-real.spec.ts).
 * Dados 100% ficticios. Respostas sao gravadas em results/fluxo/ como evidencia.
 */
const dump = (nome: string, dados: unknown) => {
  mkdirSync('results/fluxo', { recursive: true })
  writeFileSync(`results/fluxo/${nome}.json`, JSON.stringify(dados, null, 2))
}

const achado = (nivel: string, descricao: string) => {
  mkdirSync('results/fluxo', { recursive: true })
  appendFileSync('results/fluxo/achados.jsonl', JSON.stringify({ nivel, descricao }) + '\n')
  test.info().annotations.push({ type: `ACHADO-${nivel}`, description: descricao })
}

test.describe.serial('fluxo sem chave OpenAI (backend real)', () => {
  let s: Sessao
  let imovelId = 0

  test('1. cadastro do imovel', async ({ request }) => {
    s = await apiLogin(request)
    const im = await criarImovelFicticio(request, s, 'FLUXO')
    imovelId = im.id
    expect(imovelId).toBeGreaterThan(0)
  })

  test('2. upload e processamento documental (texto ficticio)', async ({ request }) => {
    const res = await request.post(`${API_URL}/api/imoveis/${imovelId}/documentos`, {
      headers: auth(s),
      multipart: {
        file: { name: 'matricula-ficticia.txt', mimeType: 'text/plain', buffer: Buffer.from(MATRICULA_FICTICIA, 'utf-8') },
        document_type: 'MATRICULA', source: 'e2e-homologacao',
      },
    })
    const corpo = await res.json().catch(() => ({}))
    dump('upload', { status: res.status(), corpo })
    expect(res.status(), 'upload deve aceitar texto ficticio').toBeLessThan(300)
    const lista = await (await request.get(`${API_URL}/api/imoveis/${imovelId}/documentos`, { headers: auth(s) })).json()
    dump('documentos', lista)
    expect(lista.documentos.length).toBe(1)
  })

  test('3. analise completa sem chave: deve ser transparente sobre a ausencia de IA', async ({ request }) => {
    const res = await request.post(`${API_URL}/api/imoveis/${imovelId}/analisar`, { headers: auth(s), data: {} })
    const corpo = await res.json()
    dump('analisar-sem-chave', { status: res.status(), corpo })
    expect(res.status()).toBe(200)
    expect(corpo.llm_usada, 'sem chave nao pode haver uso de LLM').toBe(false)
    // Comportamento DESEJADO para homologacao: nao anunciar "concluida" quando nenhum
    // agente de IA produziu resultado. Falha aqui = achado de confiabilidade (ver AUDITORIA-LLM.md).
    if ((corpo.chunks_recuperados ?? []).length === 0) achado('FALHA', 'RAG recuperou 0 chunks apesar de matricula indexada (consulta padrao + busca textual sem embedding)')
    // Registrado como ACHADO (anotacao + results/fluxo/achados.jsonl) para nao interromper a sequencia serial.
    if (corpo.status === 'concluida') achado('FALHA', 'API responde status "concluida" com 0 agentes bem-sucedidos (error_runs=' + corpo.llm_usage?.error_runs + ')')
  })

  test('4. registro de uso/custo (llm_runs) coerente', async ({ request }) => {
    const r = await request.get(`${API_URL}/api/imoveis/${imovelId}/historico`, { headers: auth(s) })
    const corpo = await r.json()
    dump('historico', { analises: corpo.analises })
    expect(corpo.analises.length).toBeGreaterThan(0)
  })

  test('5. celular (390px): detalhe do imovel e resultado visiveis', async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true })
    const page = await ctx.newPage()
    await injetarSessao(page, s)
    await page.goto(`/imoveis/${imovelId}`)
    await page.waitForLoadState('networkidle').catch(() => undefined)
    await expect(page.getByText(/HOM-FICTICIO/).first()).toBeVisible()
    mkdirSync('results/fluxo', { recursive: true })
    await page.screenshot({ path: 'results/fluxo/detalhe-390.png' })
    await ctx.close()
  })

  test('6. celular (390px): upload e analise pela INTERFACE', async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true })
    const page = await ctx.newPage()
    await injetarSessao(page, s)
    await page.goto(`/imoveis/${imovelId}`)
    await page.waitForLoadState('networkidle').catch(() => undefined)
    mkdirSync('results/fluxo', { recursive: true })

    await page.locator('.detail-nav-item', { hasText: /^\s*Documentos\s*$/ }).click()
    await page.getByRole('button', { name: /Enviar documento/ }).first().click()
    await page.getByLabel('Arquivo do documento').setInputFiles({ name: 'edital-ficticio.txt', mimeType: 'text/plain', buffer: Buffer.from('EDITAL FICTICIO. Leilao do imovel apto 45. Venda ad corpus. Debitos por conta do arrematante.') })
    await page.getByRole('button', { name: 'Confirmar envio' }).click()
    await expect(page.getByText('Envio concluído')).toBeVisible()
    await page.screenshot({ path: 'results/fluxo/ui-upload-390.png' })

    const t0 = Date.now()
    await page.getByRole('button', { name: /Executar análise completa/ }).click()
    const resultado = page.getByText(/Versão \d+ gerada/)
    await expect(resultado).toBeVisible({ timeout: 90_000 })
    const texto = (await resultado.first().innerText()).replace(/\s+/g, ' ')
    dump('ui-analise', { duracao_ms: Date.now() - t0, mensagem_exibida: texto })
    await page.screenshot({ path: 'results/fluxo/ui-analise-390.png' })
    // Transparencia: a mensagem deveria avisar que a IA nao rodou. Falha = achado.
    if (!/sem (chave|IA)|indispon|n[ãa]o (executou|utilizou)|parcial/i.test(texto)) achado('FALHA', 'UI nao informa que a IA estava indisponivel: "' + texto + '"')
    await ctx.close()
  })
})
