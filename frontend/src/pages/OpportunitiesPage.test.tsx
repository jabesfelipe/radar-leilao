import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OpportunitiesPage } from './OpportunitiesPage'

// Fixtures sintéticas isoladas — nunca o imóvel 633.
const modalities = {
  ruleset_version: 'modality-v1',
  modalidades: [
    { code: 'INDEFINIDO', name: 'Indefinido', description: 'Sem evidência', track: 'NENHUMA', status: 'ATIVO' },
    { code: 'JUDICIAL', name: 'Judicial', description: 'Hasta pública', track: 'JUDICIAL', status: 'ATIVO' },
  ],
}

const row = {
  id: 10,
  property_id: 5,
  modality: 'INDEFINIDO',
  status: 'EM_PROSPECCAO',
  municipio: 'Curitiba',
  current_phase: 'F0_INTAKE',
  blocked: false,
}

const detail = {
  oportunidade: row,
  imovel: { id: 5, title: 'Imóvel X', city: 'Curitiba', state: 'PR' },
  workflow: { current_phase: 'F0_INTAKE' },
  fase: {
    phase: 'F0_INTAKE', phase_state: 'EM_ANALISE', gate_satisfied: false, active_hard_stops: [],
    blocked: false, forward_targets: ['F1_TRIAGEM'], next_action: 'Triagem inicial', ruleset_version: 'workflow-v1',
  },
}

const transitions = {
  transicoes: [
    { allowed: true, result: 'PERMITIDA', transition_type: 'AVANCO', from_phase: 'F0_INTAKE', to_phase: 'F1_TRIAGEM', reason: 'ok', active_hard_stops: [] },
  ],
}

function jsonResponse(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

// Roteia o fetch mockado por URL+método, imitando o backend real.
function routeFetch(overrides: Record<string, unknown> = {}) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = (init?.method ?? 'GET').toUpperCase()
    if (url.includes('/api/oportunidades/modalidades')) return jsonResponse(modalities)
    if (url.match(/\/api\/oportunidades\/10\/transicoes/)) return jsonResponse(transitions)
    if (url.match(/\/api\/oportunidades\/10\/hard-stops/)) return jsonResponse({ hard_stops: [] })
    if (url.match(/\/api\/oportunidades\/10\/historico/)) return jsonResponse({ historico: [] })
    if (url.match(/\/api\/oportunidades\/10\/transicao/) && method === 'POST') {
      return jsonResponse({ decision: { ...transitions.transicoes[0] }, transition_id: 1, workflow: {} })
    }
    if (url.match(/\/api\/oportunidades\/10$/)) return jsonResponse(overrides.detail ?? detail)
    if (url.match(/\/api\/oportunidades\?/) || url.match(/\/api\/oportunidades$/)) {
      return jsonResponse(overrides.list ?? { total: 1, limit: 50, offset: 0, itens: [row] })
    }
    if (method === 'POST' && (url.match(/\/api\/oportunidades$/) || url.endsWith('/api/oportunidades'))) {
      return jsonResponse({ oportunidade: { ...row, id: 10 }, workflow: {} })
    }
    return jsonResponse({ detail: `rota não mockada: ${method} ${url}` }, false, 404)
  })
}

describe('OpportunitiesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = routeFetch() as unknown as typeof fetch
    vi.spyOn(window, 'prompt').mockReturnValue('justificativa')
  })

  it('carrega e lista oportunidades', async () => {
    render(<OpportunitiesPage />)
    expect(await screen.findByText('#5')).toBeInTheDocument()
    expect(screen.getByText('Curitiba')).toBeInTheDocument()
    expect(screen.getByText('F0_INTAKE')).toBeInTheDocument()
  })

  it('mostra estado vazio quando não há oportunidades', async () => {
    globalThis.fetch = routeFetch({ list: { total: 0, limit: 50, offset: 0, itens: [] } }) as unknown as typeof fetch
    render(<OpportunitiesPage />)
    expect(await screen.findByText('Sem oportunidades')).toBeInTheDocument()
  })

  it('abre o detalhe da oportunidade ao clicar em Abrir', async () => {
    render(<OpportunitiesPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Abrir' }))
    expect(await screen.findByText('Oportunidade #10')).toBeInTheDocument()
    // Fase e transição disponível vindas do backend (não recalculadas no front).
    await waitFor(() => expect(screen.getByText('Triagem inicial', { exact: false })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /AVANCO → F1_TRIAGEM/ })).toBeInTheDocument()
  })

  it('dispara transição de avanço pelo backend', async () => {
    const spy = routeFetch()
    globalThis.fetch = spy as unknown as typeof fetch
    render(<OpportunitiesPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Abrir' }))
    const advance = await screen.findByRole('button', { name: /AVANCO → F1_TRIAGEM/ })
    fireEvent.click(advance)
    await waitFor(() => {
      const called = spy.mock.calls.some(([u, i]) =>
        String(u).includes('/api/oportunidades/10/transicao') && (i as RequestInit | undefined)?.method === 'POST')
      expect(called).toBe(true)
    })
  })

  it('cria oportunidade a partir do ID do imóvel', async () => {
    const spy = routeFetch()
    globalThis.fetch = spy as unknown as typeof fetch
    render(<OpportunitiesPage />)
    await screen.findByText('#5')
    fireEvent.change(screen.getByLabelText('Criar p/ imóvel (ID)'), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Criar oportunidade' }))
    await waitFor(() => {
      const posted = spy.mock.calls.some(([u, i]) =>
        String(u).endsWith('/api/oportunidades') && (i as RequestInit | undefined)?.method === 'POST')
      expect(posted).toBe(true)
    })
  })
})
