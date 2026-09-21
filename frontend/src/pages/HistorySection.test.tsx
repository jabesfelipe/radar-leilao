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

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function detail(eventos: unknown[], analises: unknown[]) {
  return response({ imovel: { id: 5 }, eventos, analises })
}

describe('HistorySection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail([], []))
    render(<HistorySection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando histórico')
    expect(await screen.findByText('Nenhum histórico registrado')).toBeInTheDocument()
  })

  it('lista versões de análise e eventos reais', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail([event], [analysis]))
    render(<HistorySection propertyId={5} />)

    expect(await screen.findByText('Versões de análise')).toBeInTheDocument()
    expect(screen.getByText('Análise v2')).toBeInTheDocument()
    expect(screen.getByText('Reanálise após novo documento.')).toBeInTheDocument()
    expect(screen.getByText('Eventos')).toBeInTheDocument()
    expect(screen.getByText('IMOVEL CADASTRADO')).toBeInTheDocument()
    expect(screen.getByText('documental, financeiro')).toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/imoveis/5')
  })

  it('trata erro e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(detail([event], [analysis]))
    render(<HistorySection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('Análise v2')).toBeInTheDocument())
  })
})
