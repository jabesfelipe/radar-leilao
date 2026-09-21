import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VerdictSection } from './VerdictSection'

const verdict = {
  id: 3,
  property_id: 5,
  analysis_version: 2,
  overall: 'ATENCAO',
  summary: 'Imóvel com pendências relevantes a confirmar.',
  what_is_known: 'Documentação básica recebida.',
  what_is_unknown: 'Situação de ocupação não confirmada.',
  pending_items: ['Confirmar ocupação', 'Validar matrícula'],
  financial: {},
  risk_ids: [9, 10],
  evidence_ids: [21],
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function detail(veredito: unknown) {
  return response({ imovel: { id: 5 }, riscos: [], veredito })
}

describe('VerdictSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail(null))
    render(<VerdictSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando veredito')
    expect(await screen.findByText('Veredito não disponível')).toBeInTheDocument()
  })

  it('exibe o veredito retornado pelo backend', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail(verdict))
    render(<VerdictSection propertyId={5} />)

    expect(await screen.findByText('VEREDITO CONSOLIDADO')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Atenção' })).toBeInTheDocument()
    expect(screen.getByText('Imóvel com pendências relevantes a confirmar.')).toBeInTheDocument()
    expect(screen.getByText('Documentação básica recebida.')).toBeInTheDocument()
    expect(screen.getByText('Confirmar ocupação')).toBeInTheDocument()
    expect(screen.getByText('#9, #10')).toBeInTheDocument()
  })

  it('trata erro e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(detail(verdict))
    render(<VerdictSection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Atenção' })).toBeInTheDocument())
  })
})
