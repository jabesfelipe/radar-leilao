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
    // A seção também carrega a lista de leiloeiros (associação ao leilão). Esse
    // GET é roteado por URL para não interferir na fila de respostas do edital.
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input).includes('/api/leiloeiros')) return response([])
      return response(null)
    })
    globalThis.fetch = fetchMock as unknown as typeof fetch
  })

  // Enfileira respostas para os GETs/POSTs do EDITAL (ignora chamadas de leiloeiros).
  function queueEdital(...responses: Array<Promise<Response>>) {
    let i = 0
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input).includes('/api/leiloeiros')) return response([])
      const next = responses[i] ?? response(null)
      i += 1
      return next
    })
  }

  it('carrega e exibe o edital atual com histórico', async () => {
    queueEdital(response({ property_id: 5, atual: notice, historico: [notice], alteracoes: [] }))
    render(<AuctionNoticeSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando edital')
    expect(await screen.findByText('EDITAL ATUAL')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Edital 001/2026' })).toBeInTheDocument()
    expect(screen.getByText('2º leilão')).toBeInTheDocument()
    expect(screen.getByText('Histórico de editais')).toBeInTheDocument()
  })

  it('mostra estado vazio quando não há edital', async () => {
    queueEdital(response({ property_id: 5, atual: null, historico: [], alteracoes: [] }))
    render(<AuctionNoticeSection propertyId={5} />)

    expect(await screen.findByText('Nenhum edital cadastrado')).toBeInTheDocument()
  })

  it('valida identificador obrigatório e cadastra o edital', async () => {
    queueEdital(
      response({ property_id: 5, atual: null, historico: [], alteracoes: [] }),
      response(notice),
      response({ property_id: 5, atual: notice, historico: [notice], alteracoes: [] }),
    )
    render(<AuctionNoticeSection propertyId={5} />)
    await screen.findByText('Nenhum edital cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo edital' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar edital' }))
    expect(await screen.findByText('Informe o identificador do edital.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Identificador'), { target: { value: 'Edital 001/2026' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar edital' }))

    expect(await screen.findByText('Edital registrado com sucesso.')).toBeInTheDocument()
    // Localiza a chamada POST do edital (independente da ordem dos GETs).
    const postCall = vi.mocked(fetch).mock.calls.find(
      (c) => String(c[0]).includes('/api/imoveis/5/edital') && (c[1] as RequestInit)?.method === 'POST',
    )
    expect(postCall).toBeDefined()
    expect(JSON.parse(String((postCall![1] as RequestInit).body)).identifier).toBe('Edital 001/2026')
  })

  it('trata erro da API e permite tentar novamente', async () => {
    queueEdital(
      response({ detail: 'Falha ao carregar' }, false, 500),
      response({ property_id: 5, atual: notice, historico: [], alteracoes: [] }),
    )
    render(<AuctionNoticeSection propertyId={5} />)

    expect(await screen.findByText('Falha ao carregar')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Edital 001/2026' })).toBeInTheDocument())
  })

  it('associa um leiloeiro cadastrado ao leilão (GAP 3)', async () => {
    // fetch roteado por URL: edital atual + lista de leiloeiros + POST de associação.
    let linked = false
    globalThis.fetch = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/leilao/leiloeiro')) {
        linked = true
        return response({ property_id: 5, auction_id: 9, auctioneer_id: 7, auctioneer_nome: 'Leiloeiro X' })
      }
      if (url.includes('/api/leiloeiros')) return response([{ id: 7, name: 'Leiloeiro X', company: 'LX', status: 'ATIVO' }])
      return response({ property_id: 5, atual: notice, historico: [], alteracoes: [] })
      void init
    }) as unknown as typeof fetch

    render(<AuctionNoticeSection propertyId={5} />)
    await screen.findByText('EDITAL ATUAL')
    const select = await screen.findByLabelText('Leiloeiro cadastrado')
    fireEvent.change(select, { target: { value: '7' } })
    fireEvent.click(screen.getByRole('button', { name: 'Associar ao leilão' }))
    expect(await screen.findByText(/associado ao leilão/)).toBeInTheDocument()
    expect(linked).toBe(true)
  })
})
