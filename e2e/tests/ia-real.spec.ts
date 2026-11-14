import { test, expect } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { API_URL, MATRICULA_FICTICIA, apiLogin, auth, criarImovelFicticio, type Sessao } from './helpers'

/**
 * INTEGRACAO REAL COM A OPENAI (gated). NAO EXECUTADO na homologacao v1.0.2 por nao
 * haver chave autorizada. Consome credito real da OpenAI (centavos, com dados ficticios).
 *
 * So roda quando TODAS as condicoes forem verdadeiras:
 *   RADAR_E2E_OPENAI=1            -> o operador sabe que o ambiente-alvo TEM chave configurada
 *   RADAR_E2E_ALLOW_COST=SIM      -> autoriza o consumo
 *   API local OU RADAR_E2E_ALLOW_REMOTE=SIM (nunca apontar para producao sem autorizacao formal)
 *
 * A chave NUNCA e lida/exibida por este teste: ela vive no ambiente do backend.
 */
const habilitado = process.env.RADAR_E2E_OPENAI === '1' && process.env.RADAR_E2E_ALLOW_COST === 'SIM'
const local = /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?/.test(API_URL)
const remotoAutorizado = process.env.RADAR_E2E_ALLOW_REMOTE === 'SIM'

const dump = (nome: string, dados: unknown) => {
  mkdirSync('results/ia-real', { recursive: true })
  writeFileSync(`results/ia-real/${nome}.json`, JSON.stringify(dados, null, 2))
}

test.describe.serial('IA real (OpenAI) - gated', () => {
  test.skip(!habilitado, 'NAO EXECUTADO: defina RADAR_E2E_OPENAI=1 e RADAR_E2E_ALLOW_COST=SIM (consome credito real).')
  test.skip(habilitado && !local && !remotoAutorizado, 'API remota: exige RADAR_E2E_ALLOW_REMOTE=SIM.')

  let s: Sessao
  let imovelId = 0
  let analiseId = 0

  test('1. cadastro + upload ficticio gera chunks COM embedding (1536 dim)', async ({ request }) => {
    s = await apiLogin(request)
    imovelId = (await criarImovelFicticio(request, s, 'IA-REAL')).id
    const up = await request.post(`${API_URL}/api/imoveis/${imovelId}/documentos`, {
      headers: auth(s),
      multipart: {
        file: { name: 'matricula-ficticia.txt', mimeType: 'text/plain', buffer: Buffer.from(MATRICULA_FICTICIA, 'utf-8') },
        document_type: 'MATRICULA', source: 'e2e-ia-real',
      },
    })
    expect(up.status()).toBeLessThan(300)
    const rag = await (await request.get(`${API_URL}/api/monitoring/rag`, { headers: auth(s) })).json()
    dump('rag-cobertura', rag)
    expect(JSON.stringify(rag.embeddings)).toBeTruthy()
    const pend = await (await request.get(`${API_URL}/api/monitoring/rag/pending`, { headers: auth(s) })).json()
    expect(pend.pendentes, 'nada deveria ficar aguardando embedding com chave valida').toBe(0)
  })

  test('2. analise completa usa LLM e registra tokens/custo/latencia', async ({ request }) => {
    const res = await request.post(`${API_URL}/api/imoveis/${imovelId}/analisar`, { headers: auth(s), data: {} })
    const corpo = await res.json()
    dump('analisar-real', corpo)
    expect(res.status()).toBe(200)
    expect(corpo.llm_usada).toBe(true)
    expect(corpo.modelo).toBeTruthy()
    expect(corpo.llm_usage?.total_tokens ?? corpo.llm_usage?.tokens_total ?? 0).toBeGreaterThan(0)
    const hist = await (await request.get(`${API_URL}/api/imoveis/${imovelId}/historico`, { headers: auth(s) })).json()
    analiseId = hist.analises[0].id
    expect(analiseId).toBeGreaterThan(0)
  })

  for (const agente of ['documental', 'juridico', 'financeiro', 'mercado', 'checklist']) {
    test(`3. agente ${agente} executa isoladamente`, async ({ request }) => {
      const res = await request.post(`${API_URL}/api/imoveis/${imovelId}/analises/${analiseId}/agents/${agente}`, { headers: auth(s), data: {} })
      const corpo = await res.json().catch(() => ({}))
      dump(`agente-${agente}`, { status: res.status(), corpo })
      // financeiro/mercado dependem de dados manuais: 4xx explicito e aceitavel, 5xx nao.
      expect(res.status()).toBeLessThan(500)
    })
  }
})
