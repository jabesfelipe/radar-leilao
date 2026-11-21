import { test, expect, type Page } from '@playwright/test'
import { API_URL, apiLogin, auth, injetarSessao, type Sessao } from './helpers'

/**
 * Fluxo da inteligência do investimento (v1.0.14) com backend real local e dados 100% fictícios:
 * Resumo → pesquisa automática → Mercado → Financeiro → Riscos → Checklist → Documentos → Matrícula → Débitos (IPTU/condomínio),
 * e a consistência dos números entre Resumo, Mercado e Financeiro (mesma API). Sem provedor de pesquisa configurado no
 * ambiente de teste: a pesquisa precisa responder "não configurada" sem gravar nada.
 */
let s: Sessao
let id = 0

const MATRICULA = `MATRÍCULA Nº 99.999 - REGISTRO DE IMÓVEIS FICTÍCIO
PROPRIETÁRIA: CONSTRUTORA FICTÍCIA LTDA, inscrita no CNPJ sob nº 00.000.000/0001-00.
R-1/99.999 - Protocolo nº 1.234 de 10/01/2018. COMPRA E VENDA. Instrumento particular datado de 05/01/2018. VENDEDORA: CONSTRUTORA FICTÍCIA LTDA. COMPRADOR: FULANO FICTÍCIO. Valor: R$ 200.000,00.
R-2/99.999 - ALIENAÇÃO FIDUCIÁRIA em favor do BANCO FICTÍCIO S.A. Valor da dívida: R$ 160.000,00.
Av-3/99.999 - CONSOLIDAÇÃO DA PROPRIEDADE em nome do credor fiduciário BANCO FICTÍCIO S.A., registrado em 15/09/2025.`

async function abrir(page: Page, secao: string) {
  await page.locator('.detail-nav-item', { hasText: new RegExp(`^\\s*${secao}\\s*$`) }).first().click()
  await page.waitForLoadState('networkidle').catch(() => undefined)
}

test.beforeAll(async ({ playwright }) => {
  const req = await playwright.request.newContext()
  s = await apiLogin(req)
  const h = auth(s)
  const full = await req.post(`${API_URL}/api/imoveis/completo`, {
    headers: h,
    data: {
      imovel: { title: 'HOM-FICTICIO Inteligência', address: 'Rua Fictícia, 100', city: 'Cidade Ficticia', state: 'PR', property_type: 'Apartamento',
        neighborhood: 'Bairro Ficticio', area_m2: 50, private_area_m2: 48, bedrooms: 2, parking_spots: 1 },
      leilao: { auction_stage: 'Venda direta', appraisal_value: 220000, bid_value: 130000 },
    },
  })
  if (!full.ok()) throw new Error(`cadastro falhou ${full.status()} ${await full.text()}`)
  const body = await full.json()
  id = body.id ?? body.imovel?.id ?? body.property?.id
  const comp = (kind: string, valor: number, area: number, condo: number) => req.post(`${API_URL}/api/imoveis/${id}/comparaveis`, {
    headers: h,
    data: { kind, price: kind === 'VENDA' ? valor : 0, rent: kind === 'ALUGUEL' ? valor : null, area_m2: area, source: 'Cadastro manual fictício',
      url: `https://exemplo.invalid/${kind}/${valor}`, city: 'Cidade Ficticia', state: 'PR', neighborhood: 'Bairro Ficticio', property_type: 'Apartamento',
      bedrooms: 2, parking_spots: 1, condo_fee: condo, price_type: 'ANUNCIADO', collected_at: '2026-11-01' },
  })
  for (const [v, a, c] of [[250000, 48, 400], [255000, 49, 410], [260000, 50, 420], [248000, 47, 405]]) await comp('VENDA', v, a, c)
  for (const [v, a] of [[1300, 48], [1350, 49], [1400, 50]]) await comp('ALUGUEL', v, a, 400)
  await req.post(`${API_URL}/api/imoveis/${id}/documentos`, { headers: h, multipart: { file: { name: 'matricula-ficticia.txt', mimeType: 'text/plain', buffer: Buffer.from(MATRICULA) }, document_type: 'MATRICULA', source: 'e2e' } })
  await req.post(`${API_URL}/api/imoveis/${id}/analisar`, { headers: h, data: {} })
  await req.dispose()
})

test('números iguais entre Resumo, Mercado e Financeiro; desconhecido não vira zero', async ({ playwright }) => {
  const req = await playwright.request.newContext()
  const h = auth(s)
  const resumo = await (await req.get(`${API_URL}/api/imoveis/${id}/resumo-investimento`, { headers: h })).json()
  const intel = await (await req.get(`${API_URL}/api/imoveis/${id}/inteligencia-mercado`, { headers: h })).json()
  const base = intel.cenarios.find((c: { cenario: string }) => c.cenario === 'BASE')
  expect(resumo.numeros.valor_venda.valor).toEqual(base.valor_venda)
  expect(resumo.numeros.valor_venda.valor).not.toBeNull()
  expect(resumo.condominio.taxa_mensal.valor).toEqual(intel.carregamento_mensal.valor)
  expect(resumo.mercado.venda.qualidade.nivel).toBe('BAIXA')                       // 4 anúncios: nunca ALTA
  expect(resumo.iptu.debito_em_aberto.valor).toBeNull()                             // não consultado: desconhecido
  expect(resumo.iptu.debito_em_aberto.tipo).toBe('DESCONHECIDO')
  expect(resumo.recomendacao.codigo).not.toBe('FAVORAVEL')                          // IPTU, edital e outros faltam
  const riscos = await (await req.get(`${API_URL}/api/imoveis/${id}/riscos-consolidados`, { headers: h })).json()
  const chaves = riscos.itens.map((r: { chave: string }) => r.chave)
  expect(new Set(chaves).size).toBe(chaves.length)                                   // sem risco duplicado
  expect(JSON.stringify(riscos.itens.map((r: Record<string, unknown>) => [r.titulo, r.o_que_significa]))).not.toMatch(/CHECKLIST_|RiskEngine/)
  const pesquisa = await req.post(`${API_URL}/api/imoveis/${id}/pesquisa-automatica`, { headers: h, data: {} })
  expect(pesquisa.ok()).toBeTruthy()
  expect((await pesquisa.json()).status).toBe('NAO_CONFIGURADO')
  await req.dispose()
})

test('fluxo pelas telas', async ({ page }) => {
  await injetarSessao(page, s)
  await page.goto(`/imoveis/${id}`)
  await page.waitForLoadState('networkidle').catch(() => undefined)

  await abrir(page, 'Resumo do investimento')
  await expect(page.getByLabel('Recomendação', { exact: true })).toContainText(/ATENÇÃO — INVESTIGAR|DESFAVORÁVEL|NÃO ARREMATAR/)
  await expect(page.getByLabel('Cenários', { exact: true })).toContainText('Provável')
  await page.getByRole('button', { name: /Pesquisar automaticamente/ }).first().click()
  await expect(page.getByLabel('Pesquisa automática', { exact: true }).first()).toContainText(/NAO CONFIGURADO/)

  await abrir(page, 'Mercado')
  await expect(page.getByText('Cadastro manual fictício').first()).toBeVisible()

  await abrir(page, 'Financeiro')
  await expect(page.locator('body')).toContainText(/Financeiro/)

  await abrir(page, 'Riscos')
  await expect(page.locator('.dossier-section')).not.toContainText(/CHECKLIST_|RiskEngine|Versão da análise|Evidência #/)

  await abrir(page, 'Checklist')
  await expect(page.getByLabel('Pendências por prioridade', { exact: true })).toContainText('P0')

  await abrir(page, 'Documentos')
  await expect(page.getByLabel('Situação documental', { exact: true })).toContainText('Matrícula atualizada')

  await abrir(page, 'Matrícula')
  await page.getByRole('button', { name: 'Mostrar linha do tempo' }).click()
  await expect(page.getByLabel('Situação atual do imóvel', { exact: true })).toContainText('PROPRIETÁRIO ATUAL')

  await abrir(page, 'Débitos e despesas')
  await page.getByRole('button', { name: 'Como consultar o IPTU' }).click()
  await expect(page.getByLabel('Consulta do IPTU no município', { exact: true })).toContainText(/Pendente de consulta|Necessita informação/)
})
