import { test, expect, type Page } from '@playwright/test'
import { appendFileSync, mkdirSync } from 'node:fs'
import { API_URL, MATRICULA_FICTICIA, VIEWPORTS, apiLogin, auth, injetarSessao, type Sessao } from './helpers'

/**
 * Auditoria mobile do DETALHE do imovel com DADOS semeados (todas as 19 secoes) e do
 * wizard de cadastro. Dados 100% ficticios; backend real local; sem OpenAI.
 */
const SECOES = [
  'Visão geral', 'Cadastro', 'Leilão', 'Documentos', 'Matrícula', 'Edital', 'Processos Jurídicos',
  'Central Jurídica', 'Financeiro', 'Débitos e despesas', 'Mercado', 'Ocupação', 'Checklist',
  'Riscos', 'Veredito', 'Due Diligence', 'Pós-Arrematação', 'Histórico',
]

let s: Sessao
let imovelId = 0
// Grava em JSONL (append): o Playwright reinicia o worker apos falha e zeraria um array em memoria.
const achados = {
  push(x: unknown) {
    mkdirSync('results/mobile', { recursive: true })
    appendFileSync('results/mobile/detalhe.jsonl', JSON.stringify(x) + '\n')
  },
}

async function medir(page: Page) {
  return page.evaluate(() => {
    const W = window.innerWidth
    const desc = (e: Element) => `${e.tagName.toLowerCase()}${typeof (e as HTMLElement).className === 'string' && (e as HTMLElement).className ? '.' + (e as HTMLElement).className.trim().split(/\s+/).slice(0, 2).join('.') : ''}`
    const txt = (e: Element) => (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)
    const vis = (e: Element) => { const r = e.getBoundingClientRect(); const c = getComputedStyle(e); return r.width > 0 && r.height > 0 && c.visibility !== 'hidden' && c.display !== 'none' }
    const rolagem = (e: Element) => { let p = e.parentElement; while (p && p !== document.body && p !== document.documentElement) { const ox = getComputedStyle(p).overflowX; if ((ox === 'auto' || ox === 'scroll') && p.scrollWidth > p.clientWidth) return true; p = p.parentElement } return false }
    const fora: any[] = []; const tabelas: any[] = []; const fontes: any[] = []; const alvos: any[] = []
    for (const e of Array.from(document.querySelectorAll('body *'))) {
      if (!vis(e)) continue
      const r = e.getBoundingClientRect()
      if (r.right > W + 1 && !rolagem(e) && fora.length < 15) fora.push({ el: desc(e), direita: Math.round(r.right), texto: txt(e) })
    }
    for (const t of Array.from(document.querySelectorAll('table'))) if (vis(t) && t.getBoundingClientRect().width > W && !rolagem(t)) tabelas.push({ el: desc(t), w: Math.round(t.getBoundingClientRect().width) })
    for (const e of Array.from(document.querySelectorAll('input:not([type=hidden]),select,textarea'))) if (vis(e) && parseFloat(getComputedStyle(e).fontSize) < 16 && fontes.length < 10) fontes.push({ el: desc(e), font: parseFloat(getComputedStyle(e).fontSize) })
    for (const e of Array.from(document.querySelectorAll('a[href],button,[role=button],[role=tab]'))) { if (!vis(e)) continue; const r = e.getBoundingClientRect(); if ((r.height < 44 || r.width < 44) && alvos.length < 10) alvos.push({ el: desc(e), w: Math.round(r.width), h: Math.round(r.height), texto: txt(e) }) }
    return { fora, tabelas, fontes, alvos, scrollWidthDoc: document.documentElement.scrollWidth }
  })
}

test.beforeAll(async ({ playwright }) => {
  const req = await playwright.request.newContext()
  s = await apiLogin(req)
  const h = auth(s)
  const full = await req.post(`${API_URL}/api/imoveis/completo`, {
    headers: h,
    data: {
      imovel: { title: 'HOM-FICTICIO Detalhe Rico', address: 'Rua Ficticia Muito Longa Para Testar Quebra De Linha 12345, Bloco B, Apto 45', city: 'Sao Paulo', state: 'SP', property_type: 'Apartamento', neighborhood: 'Vila Ficticia', area_m2: 62, bedrooms: 2, parking_spots: 1, description: 'Imovel ficticio para homologacao.' },
      leilao: { auction_stage: '2º leilão', appraisal_value: 400000, bid_value: 250000, second_auction_value: 250000, auctioneer: 'Leiloeiro Ficticio', notice_url: 'https://exemplo.invalid/edital' },
      edital: { identifier: 'ED-0001/2026', item: 'Lote 1', appraisal_value: 400000, minimum_value: 250000, auctioneer: 'Leiloeiro Ficticio' },
      matricula: { registration_number: '000.000', registry_office: '1º Oficial Ficticio', comarca: 'Sao Paulo', holder: 'Titular Ficticio' },
      fontes: [{ source_type: 'PAGINA_IMOVEL', url: 'https://exemplo.invalid/imovel', description: 'Fonte ficticia' }],
    },
  })
  if (!full.ok()) throw new Error(`cadastro completo falhou ${full.status()} ${await full.text()}`)
  const body = await full.json()
  imovelId = body.id ?? body.imovel?.id ?? body.property?.id
  if (!imovelId) throw new Error('id nao encontrado: ' + JSON.stringify(body).slice(0, 300))
  for (let i = 0; i < 7; i++) {
    await req.post(`${API_URL}/api/imoveis/${imovelId}/comparaveis`, { headers: h, data: { kind: 'VENDA', price: 380000 + i * 5000, area_m2: 60 + i, source: 'Cadastro manual ficticio' } })
  }
  await req.post(`${API_URL}/api/imoveis/${imovelId}/processos`, { headers: h, data: { number: '0000000-00.2026.8.26.0000', court: 'Vara Ficticia', comarca: 'Sao Paulo', nature: 'Execucao', status: 'Em andamento', polo_active: 'Condominio Ficticio', polo_passive: 'Titular Ficticio', source: 'manual' } })
  await req.post(`${API_URL}/api/imoveis/${imovelId}/documentos`, { headers: h, multipart: { file: { name: 'matricula-ficticia.txt', mimeType: 'text/plain', buffer: Buffer.from(MATRICULA_FICTICIA) }, document_type: 'MATRICULA', source: 'e2e' } })
  await req.post(`${API_URL}/api/imoveis/${imovelId}/analisar`, { headers: h, data: {} })
  await req.dispose()
})

for (const vp of VIEWPORTS) {
  test.describe(`detalhe ${vp.nome}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height }, hasTouch: vp.width < 1000, isMobile: vp.width < 700 })

    test('18 secoes do imovel', async ({ page }) => {
      await injetarSessao(page, s)
      await page.goto(`/imoveis/${imovelId}`)
      await page.waitForLoadState('networkidle').catch(() => undefined)
      for (const nome of SECOES) {
        const botao = page.locator('.detail-nav-item', { hasText: new RegExp(`^\\s*${nome.replace(/[()]/g, '\\$&')}\\s*$`) }).first()
        const existe = await botao.count()
        if (!existe) { achados.push({ viewport: vp.nome, secao: nome, erro: 'botao de secao nao encontrado' }); continue }
        await botao.scrollIntoViewIfNeeded()
        // Alcance: o botao precisa estar visivel dentro da viewport apos rolar a barra de secoes.
        const caixa = await botao.boundingBox()
        const alcancavel = !!caixa && caixa.x >= -1 && caixa.x + caixa.width <= vp.width + 1
        await botao.click({ timeout: 5000 }).catch(() => undefined)
        await page.waitForLoadState('networkidle').catch(() => undefined)
        await page.waitForTimeout(350)
        mkdirSync('results/mobile', { recursive: true })
        await page.screenshot({ path: `results/mobile/detalhe__${vp.nome}__${nome.replace(/[^a-z0-9]/gi, '_')}.png` })
        const m = await medir(page)
        achados.push({ viewport: vp.nome, secao: nome, botaoAlcancavel: alcancavel, ...m })
        expect.soft(m.fora, `${nome}: elementos fora da tela`).toHaveLength(0)
        expect.soft(m.tabelas, `${nome}: tabelas sem rolagem`).toHaveLength(0)
      }
    })

    test('wizard de cadastro de imovel', async ({ page }) => {
      await injetarSessao(page, s)
      await page.goto('/imoveis')
      await page.waitForLoadState('networkidle').catch(() => undefined)
      const novo = page.getByRole('button', { name: /novo|cadastrar|adicionar/i }).first()
      if (!(await novo.count())) { achados.push({ viewport: vp.nome, secao: 'wizard', erro: 'botao de novo imovel nao encontrado' }); return }
      await novo.click()
      await page.waitForTimeout(500)
      await page.screenshot({ path: `results/mobile/wizard__${vp.nome}.png` })
      const m = await medir(page)
      achados.push({ viewport: vp.nome, secao: 'wizard', ...m })
      expect.soft(m.fora, 'wizard: elementos fora da tela').toHaveLength(0)
    })
  })
}
