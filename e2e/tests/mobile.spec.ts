import { test, expect } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { apiLogin, criarImovelFicticio, injetarSessao, ROTAS, VIEWPORTS, type Sessao } from './helpers'

/**
 * Auditoria mobile REAL (navegador + API reais; sem mocks).
 * O CSS do produto aplica overflow-x:hidden em html/body/.app-content, o que ESCONDE
 * overflow do scrollWidth. Por isso medimos o retangulo de cada elemento e so
 * aceitamos o que estiver dentro de um contêiner com rolagem horizontal propria.
 */

type Achados = {
  rota: string; viewport: string; largura: number
  scrollWidthDoc: number
  elementosForaDaTela: { el: string; direita: number; largura: number; texto: string }[]
  alvosPequenos: { el: string; w: number; h: number; texto: string }[]
  inputsFonteMenor16: { el: string; font: number }[]
  tabelasSemRolagem: { el: string; larguraTabela: number }[]
  textoCortado: { el: string; texto: string }[]
}

async function medir(page: import('@playwright/test').Page): Promise<Omit<Achados, 'rota' | 'viewport' | 'largura'>> {
  return page.evaluate(() => {
    const W = window.innerWidth
    const desc = (e: Element) => `${e.tagName.toLowerCase()}${(e as HTMLElement).className && typeof (e as HTMLElement).className === 'string' ? '.' + (e as HTMLElement).className.trim().split(/\s+/).slice(0, 2).join('.') : ''}`
    const txt = (e: Element) => (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)
    const visivel = (e: Element) => {
      const r = e.getBoundingClientRect(); const cs = getComputedStyle(e)
      return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'
    }
    const dentroDeRolagem = (e: Element) => {
      let p = e.parentElement
      while (p && p !== document.body && p !== document.documentElement) {
        const ox = getComputedStyle(p).overflowX
        if ((ox === 'auto' || ox === 'scroll') && p.scrollWidth > p.clientWidth) return true
        p = p.parentElement
      }
      return false
    }
    const out: any = { elementosForaDaTela: [], alvosPequenos: [], inputsFonteMenor16: [], tabelasSemRolagem: [], textoCortado: [] }
    out.scrollWidthDoc = document.documentElement.scrollWidth
    const todos = Array.from(document.querySelectorAll('body *'))
    for (const e of todos) {
      if (!visivel(e)) continue
      const r = e.getBoundingClientRect()
      if (r.right > W + 1 && !dentroDeRolagem(e) && out.elementosForaDaTela.length < 15) {
        // ignora filhos de um elemento ja reportado
        out.elementosForaDaTela.push({ el: desc(e), direita: Math.round(r.right), largura: Math.round(r.width), texto: txt(e) })
      }
    }
    const interativos = Array.from(document.querySelectorAll('a[href],button,[role=button],input:not([type=hidden]),select,textarea,[role=tab]'))
    for (const e of interativos) {
      if (!visivel(e)) continue
      const r = e.getBoundingClientRect()
      if ((r.height < 44 || r.width < 44) && out.alvosPequenos.length < 25) {
        out.alvosPequenos.push({ el: desc(e), w: Math.round(r.width), h: Math.round(r.height), texto: txt(e) })
      }
      if (/^(input|select|textarea)$/i.test(e.tagName)) {
        const fs = parseFloat(getComputedStyle(e).fontSize)
        if (fs < 16 && out.inputsFonteMenor16.length < 15) out.inputsFonteMenor16.push({ el: desc(e), font: fs })
      }
    }
    for (const t of Array.from(document.querySelectorAll('table'))) {
      if (!visivel(t)) continue
      if (t.getBoundingClientRect().width > W && !dentroDeRolagem(t)) out.tabelasSemRolagem.push({ el: desc(t), larguraTabela: Math.round(t.getBoundingClientRect().width) })
    }
    for (const b of Array.from(document.querySelectorAll('button,a[href],h1,h2,h3,.badge,.ui-badge'))) {
      if (!visivel(b)) continue
      const he = b as HTMLElement
      if (he.scrollWidth > he.clientWidth + 2 && getComputedStyle(he).overflowX !== 'visible' && out.textoCortado.length < 10) out.textoCortado.push({ el: desc(b), texto: txt(b) })
    }
    return out
  })
}

let sessao: Sessao
let imovelId = 0

test.beforeAll(async ({ playwright }) => {
  const req = await playwright.request.newContext()
  sessao = await apiLogin(req)
  imovelId = (await criarImovelFicticio(req, sessao, 'MOBILE')).id
  await req.dispose()
})

// Um arquivo por medicao: o Playwright reinicia o worker apos falha, o que zeraria
// qualquer acumulador em memoria.
function salvar(a: Achados) {
  mkdirSync('results/mobile/data', { recursive: true })
  writeFileSync(`results/mobile/data/${a.viewport}__${a.rota.replace(/[^a-z0-9]/gi, '_')}.json`, JSON.stringify(a, null, 2))
}

for (const vp of VIEWPORTS) {
  test.describe(`viewport ${vp.nome}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height }, hasTouch: vp.width < 1000, isMobile: vp.width < 700 })

    test('login pela interface', async ({ page }) => {
      await page.goto('/dashboard')
      await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible()
      await page.getByLabel('E-mail').fill(process.env.RADAR_E2E_EMAIL ?? 'hom@local.test')
      await page.getByLabel('Senha').fill(process.env.RADAR_E2E_PASSWORD ?? 'HomLocal#2026x')
      await page.getByRole('button', { name: 'Entrar' }).click()
      await expect(page.getByRole('heading', { name: 'Dashboard' }).first()).toBeVisible()
      mkdirSync('results/mobile', { recursive: true })
      await page.screenshot({ path: `results/mobile/${vp.nome}__login-ok.png` })
      const a = await medir(page)
      salvar({ rota: '(pos-login)', viewport: vp.nome, largura: vp.width, ...a })
      expect.soft(a.elementosForaDaTela, 'elementos fora da tela apos login').toHaveLength(0)
    })

    const rotas = [...ROTAS.map((r) => r as string), '__DETALHE__']
    for (const rota of rotas) {
      test(`rota ${rota}`, async ({ page }) => {
        await injetarSessao(page, sessao)
        const alvo = rota === '__DETALHE__' ? `/imoveis/${imovelId}` : rota
        await page.goto(alvo)
        await page.waitForLoadState('networkidle').catch(() => undefined)
        await page.waitForTimeout(600)
        mkdirSync('results/mobile', { recursive: true })
        await page.screenshot({ path: `results/mobile/${vp.nome}__${alvo.replace(/\//g, '_')}.png`, fullPage: false })
        const a = await medir(page)
        salvar({ rota: alvo, viewport: vp.nome, largura: vp.width, ...a })
        expect.soft(a.elementosForaDaTela, `elementos fora da tela em ${alvo}`).toHaveLength(0)
        expect.soft(a.tabelasSemRolagem, `tabelas sem rolagem em ${alvo}`).toHaveLength(0)
        if (vp.width <= 430) expect.soft(a.inputsFonteMenor16, `inputs com fonte < 16px em ${alvo}`).toHaveLength(0)
      })
    }
  })
}
