import { test, expect, type Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { API_URL, MATRICULA_FICTICIA, apiLogin, auth, injetarSessao, type Sessao } from './helpers'

/**
 * Evidências de release: capturas dos fluxos principais em celular e desktop, com checagens
 * mínimas de usabilidade (sem rolagem horizontal involuntária, menu abre e fecha, wizard cabe
 * na tela). Backend real local, dados 100% fictícios, sem OpenAI. Saída: results/release/.
 */
const RELEASE_VIEWPORTS = [
  { nome: 'android-360x800', width: 360, height: 800 },
  { nome: 'iphone-390x844', width: 390, height: 844 },
  { nome: 'android-412x915', width: 412, height: 915 },
  { nome: 'desktop-1366x768', width: 1366, height: 768 },
] as const

const SECOES = ['Visão geral', 'Documentos', 'Checklist', 'Financeiro', 'Veredito'] as const
const DIR = 'results/release'

let s: Sessao
let imovelId = 0

test.beforeAll(async ({ playwright }) => {
  const req = await playwright.request.newContext()
  s = await apiLogin(req)
  const h = auth(s)
  const full = await req.post(`${API_URL}/api/imoveis/completo`, {
    headers: h,
    data: {
      imovel: { title: 'HOM-FICTICIO Release', address: 'Rua Ficticia 123, apto 45', city: 'Sao Paulo', state: 'SP', property_type: 'Apartamento', neighborhood: 'Bairro Teste', area_m2: 62, bedrooms: 2, parking_spots: 1, description: 'Imovel ficticio para evidencias de release.' },
      leilao: { auction_stage: '2º leilão', appraisal_value: 400000, bid_value: 250000, second_auction_value: 250000, auctioneer: 'Leiloeiro Ficticio' },
    },
  })
  if (!full.ok()) throw new Error(`cadastro completo falhou ${full.status()} ${await full.text()}`)
  const body = await full.json()
  imovelId = body.id ?? body.imovel?.id ?? body.property?.id
  if (!imovelId) throw new Error('id nao encontrado: ' + JSON.stringify(body).slice(0, 300))
  await req.post(`${API_URL}/api/imoveis/${imovelId}/custos`, { headers: h, data: { category: 'REFORMA', description: 'Reforma ficticia', amount: 30000 } })
  await req.post(`${API_URL}/api/imoveis/${imovelId}/dividas`, { headers: h, data: { category: 'IPTU', creditor: 'Prefeitura Ficticia', amount: 4200 } })
  await req.post(`${API_URL}/api/imoveis/${imovelId}/documentos`, { headers: h, multipart: { file: { name: 'matricula-ficticia.txt', mimeType: 'text/plain', buffer: Buffer.from(MATRICULA_FICTICIA) }, document_type: 'MATRICULA', source: 'e2e' } })
  await req.post(`${API_URL}/api/imoveis/${imovelId}/analisar`, { headers: h, data: {} })
  await req.dispose()
})

async function semRolagemHorizontal(page: Page, onde: string) {
  const r = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, w: window.innerWidth }))
  expect.soft(r.sw, `${onde}: rolagem horizontal involuntária (${r.sw} > ${r.w})`).toBeLessThanOrEqual(r.w + 1)
}

async function captura(page: Page, vp: string, nome: string, fullPage = false) {
  mkdirSync(DIR, { recursive: true })
  await page.screenshot({ path: `${DIR}/${vp}__${nome}.png`, fullPage })
}

for (const vp of RELEASE_VIEWPORTS) {
  test.describe(`release ${vp.nome}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height }, hasTouch: vp.width < 1000, isMobile: vp.width < 700 })

    test('dashboard, navegação e listagem de imóveis', async ({ page }) => {
      await injetarSessao(page, s)
      await page.goto('/dashboard')
      await expect(page.getByRole('heading', { name: 'Dashboard' }).first()).toBeVisible()
      await captura(page, vp.nome, '01-dashboard')
      await semRolagemHorizontal(page, 'dashboard')

      if (vp.width < 1000) {
        // Menu lateral: abre, mostra o último item e fecha ao navegar.
        await page.getByRole('button', { name: 'Abrir menu' }).click()
        await expect(page.locator('.sidebar')).toHaveClass(/sidebar-open/)
        await page.waitForTimeout(400) // transição de 0,2s do menu
        const menu = await page.locator('.sidebar').boundingBox()
        expect.soft(menu && menu.x >= -1 && menu.x + menu.width <= vp.width + 1, 'menu aberto inteiro dentro da tela').toBe(true)
        await captura(page, vp.nome, '02-menu-aberto')
        await page.locator('.sidebar').getByText('Imóveis', { exact: true }).first().click()
        await expect(page.locator('.sidebar')).not.toHaveClass(/sidebar-open/)
      } else {
        await page.locator('.sidebar').getByText('Imóveis', { exact: true }).first().click()
      }
      await expect(page).toHaveURL(/\/imoveis/)
      await page.waitForLoadState('networkidle').catch(() => undefined)
      await expect(page.getByText('HOM-FICTICIO Release').first()).toBeVisible()
      await captura(page, vp.nome, '03-imoveis')
      await semRolagemHorizontal(page, 'imoveis')

      // Wizard (modal de cadastro) precisa caber na largura da tela.
      await page.getByRole('button', { name: /Novo imóvel/ }).first().click()
      await page.waitForTimeout(400)
      await captura(page, vp.nome, '04-wizard')
      await semRolagemHorizontal(page, 'wizard')
    })

    test('detalhe do imóvel: seções principais', async ({ page }) => {
      await injetarSessao(page, s)
      await page.goto(`/imoveis/${imovelId}`)
      await page.waitForLoadState('networkidle').catch(() => undefined)
      for (const [i, nome] of SECOES.entries()) {
        const botao = page.locator('.detail-nav-item', { hasText: new RegExp(`^\\s*${nome}\\s*$`) }).first()
        await expect(botao, `seção ${nome}`).toHaveCount(1)
        await botao.scrollIntoViewIfNeeded()
        await botao.click()
        await page.waitForLoadState('networkidle').catch(() => undefined)
        await page.waitForTimeout(350)
        await captura(page, vp.nome, `1${i}-detalhe-${nome.normalize('NFD').replace(/[^a-z0-9]/gi, '').toLowerCase()}`, true)
        await semRolagemHorizontal(page, `detalhe/${nome}`)
      }
    })
  })
}
