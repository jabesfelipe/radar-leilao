import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HistorySection } from './HistorySection'

const event = {
  id: 40,
  property_id: 5,
  event_type: 'IMOVEL_CADASTRADO',
  aggregate_type: 'Property',
  aggregate_id: 5,
  affected_domains: ['documental', 'financeiro'],
  processed: true,
  created_at: '2026-01-10T12:00:00Z',
}

const analysis = {
  id: 12,
  property_id: 5,
  version: 2,
  scope: 'Completa',
  agents_executed: ['documental', 'financeiro'],
  changes: 'Reanálise após novo documento.',
  created_at: '2026-01-11T09:00:00Z',
}

const change = {
  id: 88,
  property_id: 5,
  entity_type: 'Cost',
  entity_id: 3,
  action: 'UPDATED',
  actor: 'sistema',
  created_at: '2026-01-11T10:30:00Z',
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function history(eventos: unknown[], alteracoes: unknown[], analises: unknown[]) {
  return response({ eventos, alteracoes, analises })
}

describe('HistorySection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('consome o endpoint /historico', async () => {
    vi.mocked(fetch).mockReturnValueOnce(history([], [], []))
    render(<HistorySection propertyId={5} />)

    await screen.findByText('Nenhum histórico registrado')
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/imoveis/5/historico')
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(history([], [], []))
    render(<HistorySection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando histórico')
    expect(await screen.findByText('Nenhum histórico registrado')).toBeInTheDocument()
  })

  it('lista versões de análise, alterações e eventos reais', async () => {
    vi.mocked(fetch).mockReturnValueOnce(history([event], [change], [analysis]))
    render(<HistorySection propertyId={5} />)

    expect(await screen.findByText('Versões de análise')).toBeInTheDocument()
    expect(screen.getByText('Análise v2')).toBeInTheDocument()
    expect(screen.getByText('Reanálise após novo documento.')).toBeInTheDocument()

    expect(screen.getByText('Alterações')).toBeInTheDocument()
    expect(screen.getByText('Cost #3')).toBeInTheDocument()
    expect(screen.getByText('UPDATED')).toBeInTheDocument()
    expect(screen.getByText('por sistema')).toBeInTheDocument()

    expect(screen.getByText('Eventos')).toBeInTheDocument()
    expect(screen.getByText('IMOVEL CADASTRADO')).toBeInTheDocument()
    expect(screen.getByText('documental, financeiro')).toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/imoveis/5/historico')
  })

  it('trata erro e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(history([event], [change], [analysis]))
    render(<HistorySection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('Análise v2')).toBeInTheDocument())
  })
})
