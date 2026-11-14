import type { APIRequestContext, Page } from '@playwright/test'

export const API_URL = process.env.RADAR_E2E_API_URL ?? 'http://127.0.0.1:8100'
export const EMAIL = process.env.RADAR_E2E_EMAIL ?? 'hom@local.test'
export const PASSWORD = process.env.RADAR_E2E_PASSWORD ?? 'HomLocal#2026x'

export const VIEWPORTS = [
  { nome: 'android-360x800', width: 360, height: 800 },
  { nome: 'iphone-375x812', width: 375, height: 812 },
  { nome: 'iphone-390x844', width: 390, height: 844 },
  { nome: 'android-412x915', width: 412, height: 915 },
  { nome: 'iphone-430x932', width: 430, height: 932 },
  { nome: 'tablet-768x1024', width: 768, height: 1024 },
  { nome: 'desktop-1366x768', width: 1366, height: 768 },
] as const

export const ROTAS = [
  '/dashboard', '/oportunidades', '/imoveis', '/documentos', '/juridico', '/financeiro',
  '/mercado', '/ocupacao', '/checklist', '/riscos', '/veredito', '/historico',
  '/leiloeiros', '/administracao',
] as const

export type Sessao = { token: string; user: unknown }

/**
 * Mede o layout de verdade (retângulos), ignorando o que estiver dentro de contêiner com rolagem
 * horizontal própria. O CSS do produto usa overflow-x:hidden em html/body/.app-content, que esconde
 * overflow do scrollWidth.
 */
export async function medirLayout(page: Page) {
  return page.evaluate(() => {
    const W = window.innerWidth
    const desc = (e: Element) => `${e.tagName.toLowerCase()}${typeof (e as HTMLElement).className === 'string' && (e as HTMLElement).className ? '.' + (e as HTMLElement).className.trim().split(/\s+/).slice(0, 2).join('.') : ''}`
    const vis = (e: Element) => { const r = e.getBoundingClientRect(); const c = getComputedStyle(e); return r.width > 0 && r.height > 0 && c.visibility !== 'hidden' && c.display !== 'none' }
    const rolagem = (e: Element) => { let p = e.parentElement; while (p && p !== document.body && p !== document.documentElement) { const ox = getComputedStyle(p).overflowX; if ((ox === 'auto' || ox === 'scroll') && p.scrollWidth > p.clientWidth) return true; p = p.parentElement } return false }
    const fora: { el: string; direita: number }[] = []; const tabelas: { el: string; w: number }[] = []; const fontes: { el: string; font: number }[] = []; const botoesBaixos: { el: string; h: number }[] = []
    for (const e of Array.from(document.querySelectorAll('body *'))) {
      if (!vis(e)) continue
      const r = e.getBoundingClientRect()
      if (r.right > W + 1 && !rolagem(e) && fora.length < 15) fora.push({ el: desc(e), direita: Math.round(r.right) })
    }
    for (const t of Array.from(document.querySelectorAll('table'))) {
      if (!vis(t)) continue
      const own = getComputedStyle(t).overflowX
      const scrollable = (own === 'auto' || own === 'scroll') || rolagem(t)
      if (t.getBoundingClientRect().width > W + 1 && !scrollable) tabelas.push({ el: desc(t), w: Math.round(t.getBoundingClientRect().width) })
    }
    for (const e of Array.from(document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file]),select,textarea'))) {
      if (vis(e) && parseFloat(getComputedStyle(e).fontSize) < 16) fontes.push({ el: desc(e), font: parseFloat(getComputedStyle(e).fontSize) })
    }
    for (const e of Array.from(document.querySelectorAll('button.ui-button,button.detail-nav-item,button.admin-tab,button.wizard-step'))) {
      if (vis(e) && e.getBoundingClientRect().height < 43.5) botoesBaixos.push({ el: desc(e), h: Math.round(e.getBoundingClientRect().height) })
    }
    return { fora, tabelas, fontes, botoesBaixos, scrollWidthDoc: document.documentElement.scrollWidth }
  })
}

/** Login real na API (nao e mock). */
export async function apiLogin(request: APIRequestContext): Promise<Sessao> {
  const res = await request.post(`${API_URL}/api/auth/login`, { data: { email: EMAIL, password: PASSWORD } })
  if (!res.ok()) throw new Error(`login falhou: HTTP ${res.status()}`)
  const body = await res.json()
  const token = body.access_token as string
  const me = await request.get(`${API_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
  const meBody = await me.json()
  return { token, user: meBody.user }
}

/** Injeta a sessao no localStorage antes de qualquer script da pagina. */
export async function injetarSessao(page: Page, s: Sessao) {
  await page.addInitScript(({ token, user }) => {
    localStorage.setItem('radar.auth.token', token)
    localStorage.setItem('radar.auth.user', JSON.stringify(user))
  }, s)
}

export function auth(s: Sessao) {
  return { Authorization: `Bearer ${s.token}` }
}

/** Imovel 100% ficticio (nenhum dado real). */
export async function criarImovelFicticio(request: APIRequestContext, s: Sessao, sufixo = Date.now().toString()) {
  const res = await request.post(`${API_URL}/api/imoveis`, {
    headers: auth(s),
    data: {
      title: `HOM-FICTICIO ${sufixo}`,
      address: 'Rua Ficticia 123, apto 45',
      city: 'Sao Paulo', state: 'SP', property_type: 'Apartamento',
      neighborhood: 'Bairro Teste', area_m2: 62, bedrooms: 2, parking_spots: 1,
      description: 'Registro ficticio criado pelo E2E de homologacao.',
    },
  })
  if (!res.ok()) throw new Error(`criar imovel falhou: HTTP ${res.status()} ${await res.text()}`)
  return (await res.json()) as { id: number; title: string }
}

/** Texto ficticio que imita uma matricula (sem dados pessoais reais). */
export const MATRICULA_FICTICIA = `MATRICULA N. 000.000 - REGISTRO DE IMOVEIS FICTICIO
Imovel: apartamento 45, bloco B, Rua Ficticia 123, Sao Paulo/SP, area privativa 62,00 m2.
R.1 - Proprietario: FULANO DE TAL FICTICIO, CPF 000.000.000-00.
AV.2 - Alienacao fiduciaria em favor de BANCO FICTICIO S.A.
AV.3 - Consolidacao da propriedade em nome do credor fiduciario.
Nao constam penhoras, arrestos ou indisponibilidades.
`
