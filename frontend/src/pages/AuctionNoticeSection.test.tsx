import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuctionNoticeSection } from './AuctionNoticeSection'

const notice = {
  id: 4,
  property_id: 5,
  identifier: 'Edital 001/2026',
  notice_date: '2026-02-01',
  auction_stage: '2º leilão',
  appraisal_value: 300000,
  minimum_value: 180000,
  auction_date: '2026-03-01',
  auctioneer: 'Leiloeiro Oficial',
  observations: 'Bem ocupado',
  document_version_id: 12,
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('AuctionNoticeSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('carrega e exibe o edital atual com histórico', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ property_id: 5, atual: notice, historico: [notice], alteracoes: [] }))
    render(<AuctionNoticeSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando edital')
    expect(await screen.findByText('EDITAL ATUAL')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Edital 001/2026' })).toBeInTheDocument()
    expect(screen.getByText('2º leilão')).toBeInTheDocument()
    expect(screen.getByText('Histórico de editais')).toBeInTheDocument()
  })

  it('mostra estado vazio quando não há edital', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ property_id: 5, atual: null, historico: [], alteracoes: [] }))
    render(<AuctionNoticeSection propertyId={5} />)

    expect(await screen.findByText('Nenhum edital cadastrado')).toBeInTheDocument()
  })

  it('valida identificador obrigatório e cadastra o edital', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ property_id: 5, atual: null, historico: [], alteracoes: [] }))
      .mockReturnValueOnce(response(notice))
      .mockReturnValueOnce(response({ property_id: 5, atual: notice, historico: [notice], alteracoes: [] }))
    render(<AuctionNoticeSection propertyId={5} />)
    await screen.findByText('Nenhum edital cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo edital' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar edital' }))
    expect(await screen.findByText('Informe o identificador do edital.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Identificador'), { target: { value: 'Edital 001/2026' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar edital' }))

    expect(await screen.findByText('Edital registrado com sucesso.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[1]
    expect(postCall[0]).toContain('/api/imoveis/5/edital')
    expect(JSON.parse(String((postCall[1] as RequestInit).body)).identifier).toBe('Edital 001/2026')
  })

  it('trata erro da API e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha ao carregar' }, false, 500))
      .mockReturnValueOnce(response({ property_id: 5, atual: notice, historico: [], alteracoes: [] }))
    render(<AuctionNoticeSection propertyId={5} />)

    expect(await screen.findByText('Falha ao carregar')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Edital 001/2026' })).toBeInTheDocument())
  })
})
