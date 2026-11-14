import { defineConfig } from '@playwright/test'

/**
 * E2E de homologacao do Radar Leilao.
 *
 * Nao sobe servidores: espera um ambiente ja em execucao (ver e2e/README.md).
 *   RADAR_E2E_FRONT_URL  (padrao http://127.0.0.1:5180)
 *   RADAR_E2E_API_URL    (padrao http://127.0.0.1:8100)
 *   RADAR_E2E_EMAIL / RADAR_E2E_PASSWORD  (usuario ADMIN do ambiente de teste)
 *   RADAR_E2E_BROWSER_CHANNEL (padrao "chrome"; use "" para o Chromium do Playwright)
 *
 * NUNCA aponte para producao: o fluxo cria imoveis e documentos ficticios.
 */
const channel = process.env.RADAR_E2E_BROWSER_CHANNEL ?? 'chrome'

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: 'results/report.json' }]],
  outputDir: 'results/artifacts',
  use: {
    baseURL: process.env.RADAR_E2E_FRONT_URL ?? 'http://127.0.0.1:5180',
    channel: channel || undefined,
    headless: true,
    trace: 'off',
    screenshot: 'off',
  },
})
