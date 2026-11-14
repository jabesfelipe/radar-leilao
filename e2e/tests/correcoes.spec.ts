import { test, expect, type APIRequestContext } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { API_URL, MATRICULA_FICTICIA, VIEWPORTS, apiLogin, auth, criarImovelFicticio, injetarSessao, medirLayout, type Sessao } from './helpers'

/**
 * Rodada de correções P0/P1 (homologação v1.0.2) — prova em NAVEGADOR + BACKEND REAIS, sem OpenAI.
 * O que NÃO é provado aqui (depende de chave real): embeddings, chamadas de agentes, custos reais.
 * Dados 100% fictícios. Evidências em results/correcoes/.
 */
const dump = (nome: string, dados: unknown) => {
  mkdirSync('results/correcoes', { recursive: true })
  writeFileSync(`results/correcoes/${nome}.json`, JSON.stringify(dados, null, 2))
}

// PDF de uma página sem camada de texto (equivale a um documento escaneado).
const PDF_SEM_TEXTO = Buffer.from(
  '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n' +
  '3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R/Size 4>>\n%%EOF\n', 'latin1')

const MATRICULA_COM_CPF = `${MATRICULA_FICTICIA}\nProprietário: FULANO DE TAL FICTICIO, CPF 111.444.777-35, e-mail fulano@example.invalid.\n`

async function upload(request: APIRequestContext, s: Sessao, id: number, nome: string, buffer: Buffer, tipo: string, mime = 'text/plain') {
  const res = await request.post(`${API_URL}/api/imoveis/${id}/documentos`, { headers: auth(s), multipart: { file: { name: nome, mimeType: mime, buffer }, document_type: tipo, source: 'e2e-correcoes' } })
  expect(res.status(), `upload ${nome}`).toBeLessThan(300)
  return res.json()
}

test.describe.serial('P0 — confiabilidade (API real, sem chave)', () => {
  let s: Sessao
  let id = 0

  test('1. documentos: etapas explícitas, prontidão e nenhum caminho do servidor na resposta', async ({ request }) => {
    s = await apiLogin(request)
    id = (await criarImovelFicticio(request, s, 'CORRECOES')).id
    const doc = await upload(request, s, id, 'matricula.txt', Buffer.from(MATRICULA_COM_CPF), 'MATRICULA')
    const v = doc.versions[0]
    dump('upload-texto', doc)
    expect(v.processamento.estado).toBe('PRONTO_SEM_EMBEDDING')
    expect(v.processamento.pronto_para_analise).toBe(true)
    expect(v.processamento.nivel_indexacao).toBe('texto')
    expect(v.processamento.etapas.map((e: { etapa: string }) => e.etapa)).toEqual(['upload', 'ocr', 'extracao', 'chunking', 'embedding', 'indexacao'])
    expect(JSON.stringify(doc)).not.toMatch(/original_path|normalized_path|\/tmp\/|\/app\//)   // sem topologia do servidor
    expect(v.status).not.toBe('INDEXADO')                                                      // sem embedding NUNCA é indexado
  })

  test('2. documento digitalizado sem texto NÃO fica pronto (OCR necessário)', async ({ request }) => {
    const doc = await upload(request, s, id, 'escaneado.pdf', PDF_SEM_TEXTO, 'MATRICULA', 'application/pdf')
    dump('upload-escaneado', doc)
    const v = doc.versions[0]
    expect(v.processamento.estado).toBe('OCR_NECESSARIO')
    expect(v.processamento.pronto_para_analise).toBe(false)
    expect(doc.status).toBe('OCR_NECESSARIO')
    const ocr = v.processamento.etapas.find((e: { etapa: string }) => e.etapa === 'ocr')
    expect(ocr.estado).toBe('indisponivel')
  })

  test('3. análise sem chave: status falha/IA_INDISPONIVEL, RAG recupera trechos e há aviso do documento não pronto', async ({ request }) => {
    const res = await request.post(`${API_URL}/api/imoveis/${id}/analisar`, { headers: auth(s), data: {} })
    const corpo = await res.json()
    dump('analisar', corpo)
    expect(res.status()).toBe(200)
    expect(corpo.status).toBe('falha')
    expect(corpo.status_detalhe.codigo).toBe('IA_INDISPONIVEL')
    expect(corpo.status_detalhe.ia_disponivel).toBe(false)
    expect(corpo.status_detalhe.agentes_ok).toBe(0)
    expect(corpo.chunks_recuperados.length, 'RAG deve recuperar a matrícula (antes: 0 chunks)').toBeGreaterThan(0)
    expect(corpo.status_detalhe.avisos.join(' ')).toMatch(/escaneado\.pdf.*OCR_NECESSARIO/)
    const detalhe = await (await request.get(`${API_URL}/api/imoveis/${id}`, { headers: auth(s) })).json()
    expect(detalhe.analise_ultima.status).toBe('falha')
    expect(detalhe.analise_em_processamento).toBe(false)
  })

  test('4. agente por domínio (juridico) agora recupera contexto filtrado por categoria', async ({ request }) => {
    const hist = await (await request.get(`${API_URL}/api/imoveis/${id}/historico`, { headers: auth(s) })).json()
    const analiseId = hist.analises[hist.analises.length - 1].id
    const res = await request.post(`${API_URL}/api/imoveis/${id}/analises/${analiseId}/agents/juridico`, { headers: auth(s), data: {} })
    const corpo = await res.json()
    dump('agente-juridico', corpo)
    expect(corpo.status).toBe('SEM_CHAVE')                       // honesto: IA indisponível
    expect(corpo.chunks_recuperados.length, 'filtro category=juridico deve achar a matrícula (antes: 0)').toBeGreaterThan(0)
  })

  test('5. PDF sem texto sozinho: análise não é "concluida" nem apresenta documento como base', async ({ request }) => {
    const outro = (await criarImovelFicticio(request, s, 'SO-ESCANEADO')).id
    await upload(request, s, outro, 'escaneado.pdf', PDF_SEM_TEXTO, 'MATRICULA', 'application/pdf')
    const corpo = await (await request.post(`${API_URL}/api/imoveis/${outro}/analisar`, { headers: auth(s), data: {} })).json()
    expect(corpo.status).not.toBe('concluida')
    expect(corpo.chunks_recuperados).toEqual([])
    expect(corpo.status_detalhe.documentos_prontos).toBe(0)
  })
})

test.describe.serial('P0 — interface no celular (390px, backend real, sem chave)', () => {
  let s: Sessao
  let id = 0

  test('upload pronto-por-texto, upload digitalizado e análise sem IA são apresentados com honestidade', async ({ browser, request }) => {
    s = await apiLogin(request)
    id = (await criarImovelFicticio(request, s, 'UI-CORRECOES')).id
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true })
    const page = await ctx.newPage()
    await injetarSessao(page, s)
    await page.goto(`/imoveis/${id}`)
    await page.waitForLoadState('networkidle').catch(() => undefined)
    await page.locator('.detail-nav-item', { hasText: /^\s*Documentos\s*$/ }).click()

    // 1) texto digital: "Pronto (só texto)", jamais "Indexado"
    await page.getByRole('button', { name: /Enviar documento/ }).first().click()
    await page.getByLabel('Arquivo do documento').setInputFiles({ name: 'matricula.txt', mimeType: 'text/plain', buffer: Buffer.from(MATRICULA_FICTICIA) })
    await page.getByRole('button', { name: 'Confirmar envio' }).click()
    await expect(page.getByText('Envio concluído')).toBeVisible()
    await expect(page.getByText('Pronto (só texto)')).toBeVisible()
    await expect(page.getByText('Indexado', { exact: true })).toHaveCount(0)

    // 2) digitalizado: aceito, mas NÃO pronto
    await page.getByRole('button', { name: /Enviar documento/ }).first().click()
    await page.getByLabel('Arquivo do documento').setInputFiles({ name: 'escaneado.pdf', mimeType: 'application/pdf', buffer: PDF_SEM_TEXTO })
    await page.getByRole('button', { name: 'Confirmar envio' }).click()
    await expect(page.getByText('Documento não pronto para análise')).toBeVisible()
    await expect(page.getByText('OCR necessário')).toBeVisible()
    await page.getByRole('button', { name: /escaneado\.pdf/ }).click()
    const etapas = page.getByRole('list', { name: /Etapas de processamento/ })
    await expect(etapas).toContainText('OCR')
    await expect(etapas).toContainText('Indisponível')
    await page.screenshot({ path: 'results/correcoes/ui-documento-ocr-390.png' })

    // 3) análise sem chave: nunca "Análise concluída"
    await page.getByRole('button', { name: /Executar análise completa/ }).click()
    await expect(page.getByText('Análise sem resultado da IA')).toBeVisible({ timeout: 60_000 })
    await expect(page.getByText('Análise concluída')).toHaveCount(0)
    await expect(page.getByText(/A IA não está disponível/)).toBeVisible()
    await expect(page.locator('.ui-alert-danger').filter({ hasText: 'Análise sem resultado da IA' })).toBeVisible()
    await page.screenshot({ path: 'results/correcoes/ui-analise-falha-390.png' })

    // 4) reabrir o imóvel: a última análise continua sinalizada como falha
    await page.reload()
    await page.waitForLoadState('networkidle').catch(() => undefined)
    await expect(page.getByText(/Última análise \(v\d+\): falha/)).toBeVisible()

    // 5) histórico mostra o status
    await page.locator('.detail-nav-item', { hasText: /^\s*Histórico\s*$/ }).click()
    await expect(page.locator('.history-card').first()).toContainText('Falha')
    await ctx.close()
  })
})

// ---------------------------------------------------------------------------------------------
// P1 — layout nos 5 viewports (asserções FORTES: o que foi corrigido não pode regredir)
// ---------------------------------------------------------------------------------------------
const SECOES_CORRIGIDAS = ['Histórico', 'Central Jurídica', 'Due Diligence', 'Financeiro', 'Débitos e despesas', 'Visão geral']

test.describe('P1 — layout corrigido', () => {
  let s: Sessao
  let imovelId = 0

  test.beforeAll(async ({ playwright }) => {
    const req = await playwright.request.newContext()
    s = await apiLogin(req)
    const h = auth(s)
    const full = await req.post(`${API_URL}/api/imoveis/completo`, {
      headers: h,
      data: {
        imovel: { title: 'HOM-FICTICIO Layout', address: 'Rua Ficticia Muito Longa Para Testar Quebra De Linha 12345, Bloco B, Apto 45', city: 'Sao Paulo', state: 'SP', property_type: 'Apartamento', area_m2: 62, bedrooms: 2 },
        leilao: { auction_stage: '2º leilão', appraisal_value: 400000, bid_value: 250000, second_auction_value: 250000, auctioneer: 'Leiloeiro Ficticio' },
        edital: { identifier: 'ED-0001/2026', item: 'Lote 1', appraisal_value: 400000, minimum_value: 250000 },
        matricula: { registration_number: '000.000', registry_office: '1º Oficial Ficticio', comarca: 'Sao Paulo' },
      },
    })
    imovelId = (await full.json()).id
    await upload(req, s, imovelId, 'matricula.txt', Buffer.from(MATRICULA_FICTICIA), 'MATRICULA')
    await req.post(`${API_URL}/api/imoveis/${imovelId}/analisar`, { headers: h, data: {} })
    await req.post(`${API_URL}/api/imoveis/${imovelId}/processos`, { headers: h, data: { number: '0000000-00.2026.8.26.0000', court: 'Vara Ficticia', comarca: 'Sao Paulo', polo_active: 'Condominio Ficticio', polo_passive: 'Titular Ficticio' } })
    // dados administrativos para exercitar tabelas reais
    await req.post(`${API_URL}/api/admin/municipios`, { headers: h, data: { name: 'Municipio Ficticio com Nome Bem Longo Para Testar Tabela', state: 'SP' } })
    await req.dispose()
  })

  for (const vp of VIEWPORTS) {
    test.describe(`viewport ${vp.nome}`, () => {
      test.use({ viewport: { width: vp.width, height: vp.height }, hasTouch: vp.width < 1000, isMobile: vp.width < 700 })
      const toque = vp.width < 1000

      test('Oportunidades', async ({ page }) => {
        await injetarSessao(page, s)
        await page.goto('/oportunidades'); await page.waitForLoadState('networkidle').catch(() => undefined)
        const m = await medirLayout(page)
        mkdirSync('results/correcoes', { recursive: true })
        await page.screenshot({ path: `results/correcoes/oportunidades__${vp.nome}.png` })
        expect(m.fora, 'elementos fora da tela').toEqual([])
        if (vp.width <= 430) expect(m.fontes, 'campos < 16px').toEqual([])
      })

      test('seções do imóvel corrigidas', async ({ page }) => {
        await injetarSessao(page, s)
        await page.goto(`/imoveis/${imovelId}`); await page.waitForLoadState('networkidle').catch(() => undefined)
        for (const nome of SECOES_CORRIGIDAS) {
          await page.locator('.detail-nav-item', { hasText: new RegExp(`^\\s*${nome}\\s*$`) }).first().click()
          await page.waitForLoadState('networkidle').catch(() => undefined)
          await page.waitForTimeout(250)
          const m = await medirLayout(page)
          await page.screenshot({ path: `results/correcoes/secao__${vp.nome}__${nome.replace(/[^a-z0-9]/gi, '_')}.png` })
          expect(m.fora, `${nome}: elementos fora da tela`).toEqual([])
          expect(m.tabelas, `${nome}: tabelas sem rolagem`).toEqual([])
          if (vp.width <= 430) expect(m.fontes, `${nome}: campos < 16px`).toEqual([])
          if (toque && vp.width <= 430) expect(m.botoesBaixos, `${nome}: alvos de toque < 44px`).toEqual([])
        }
      })

      test('Administração: abas e tabelas com dados reais', async ({ page }) => {
        await injetarSessao(page, s)
        await page.goto('/administracao'); await page.waitForLoadState('networkidle').catch(() => undefined)
        const abas = page.locator('.admin-tab')
        const total = await abas.count()
        expect(total).toBeGreaterThan(3)
        let tabelasVistas = 0
        for (let i = 0; i < total; i++) {
          await abas.nth(i).click()
          await page.waitForLoadState('networkidle').catch(() => undefined)
          await page.waitForTimeout(200)
          tabelasVistas += await page.locator('table:visible').count()
          const m = await medirLayout(page)
          expect(m.fora, `aba ${i}: elementos fora da tela`).toEqual([])
          expect(m.tabelas, `aba ${i}: tabelas sem rolagem`).toEqual([])
          if (vp.width <= 430) expect(m.fontes, `aba ${i}: campos < 16px`).toEqual([])
        }
        dump(`admin-tabelas-${vp.nome}`, { abas: total, tabelasVistas })
        expect(tabelasVistas, 'o teste precisa ter exercitado tabelas reais').toBeGreaterThan(0)
      })

      test('Wizard de cadastro: campos sem zoom no iOS', async ({ page }) => {
        await injetarSessao(page, s)
        await page.goto('/imoveis'); await page.waitForLoadState('networkidle').catch(() => undefined)
        await page.getByRole('button', { name: /novo|cadastrar|adicionar/i }).first().click()
        await page.waitForTimeout(400)
        const m = await medirLayout(page)
        expect(m.fora).toEqual([])
        if (vp.width <= 430) expect(m.fontes).toEqual([])
      })
    })
  }
})
