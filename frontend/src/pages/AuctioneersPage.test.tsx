import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuctioneersPage } from './AuctioneersPage'

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

const auctioneer = {
  id: 1, name: 'Leiloeiro X', company: 'LX', status: 'ATIVO',
  portais: [{ id: 10, auctioneer_id: 1, portal: 'Caixa', username: 'u@x', has_secret: true, two_factor_enabled: true, status: 'ATIVO' }],
  documentos: [],
}

describe('AuctioneersPage', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('carrega e lista leiloeiros com portal (sem expor senha)', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([auctioneer]))
    render(<AuctioneersPage />)
    expect(await screen.findByRole('heading', { name: 'Leiloeiro X' })).toBeInTheDocument()
    expect(screen.getByText('Caixa')).toBeInTheDocument()
    expect(screen.getByText(/credencial salva/)).toBeInTheDocument()
    // Nenhuma senha é renderizada na listagem.
    expect(screen.queryByText(/senha/i)).not.toBeInTheDocument()
  })

  it('estado vazio quando não há leiloeiros', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([]))
    render(<AuctioneersPage />)
    expect(await screen.findByText('Nenhum leiloeiro')).toBeInTheDocument()
  })

  it('cadastra um leiloeiro', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response([]))
      .mockReturnValueOnce(response({ id: 2, name: 'Novo', status: 'ATIVO', portais: [], documentos: [] }, true, 201))
      .mockReturnValueOnce(response([{ id: 2, name: 'Novo', status: 'ATIVO', portais: [], documentos: [] }]))
    render(<AuctioneersPage />)
    await screen.findByText('Nenhum leiloeiro')
    fireEvent.click(screen.getAllByRole('button', { name: /Novo leiloeiro/ })[0])
    fireEvent.change(screen.getByLabelText('Nome'), { target: { value: 'Novo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar leiloeiro' }))
    expect(await screen.findByText('Leiloeiro cadastrado.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[1]
    expect(postCall[0]).toContain('/api/leiloeiros')
  })

  it('revela a credencial apenas via ação explícita (endpoint dedicado)', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response([auctioneer]))
      .mockReturnValueOnce(response({ portal_id: 10, username: 'u@x', secret: 'minha-senha' }))
    render(<AuctioneersPage />)
    await screen.findByRole('heading', { name: 'Leiloeiro X' })
    fireEvent.click(screen.getByRole('button', { name: /Ver credencial/ }))
    await waitFor(() => expect(screen.getByText('minha-senha')).toBeInTheDocument())
    const revealCall = vi.mocked(fetch).mock.calls[1]
    expect(revealCall[0]).toContain('/portais/10/credencial')
  })
})
