import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RiskSection } from './RiskSection'

const risk = {
  id: 9,
  property_id: 5,
  category: 'JURIDICO',
  description: 'Processo de execução ativo sobre o imóvel.',
  severity: 'ALTA',
  impact: 'Possível constrição judicial',
  confidence: 'MEDIA',
  status: 'ATIVO',
  origin: 'Motor determinístico',
  evidence_id: 21,
  analysis_version: 2,
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function detail(riscos: unknown[]) {
  return response({ imovel: { id: 5 }, riscos, veredito: null })
}

describe('RiskSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail([]))
    render(<RiskSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando riscos')
    expect(await screen.findByText('Nenhum risco identificado')).toBeInTheDocument()
  })

  it('lista os riscos com os campos existentes do backend', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail([risk]))
    render(<RiskSection propertyId={5} />)

    expect(await screen.findByText('JURIDICO')).toBeInTheDocument()
    expect(screen.getByText('Processo de execução ativo sobre o imóvel.')).toBeInTheDocument()
    expect(screen.getByText('Alta')).toBeInTheDocument()
    expect(screen.getByText('Possível constrição judicial')).toBeInTheDocument()
    expect(screen.getByText('#21')).toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/imoveis/5')
  })

  it('trata erro e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(detail([risk]))
    render(<RiskSection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('JURIDICO')).toBeInTheDocument())
  })
})
