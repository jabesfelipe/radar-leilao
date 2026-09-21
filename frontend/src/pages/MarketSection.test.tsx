import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MarketSection } from './MarketSection'

const comparable = { id: 1, property_id: 5, kind: 'VENDA', price: 300000, rent: null, area_m2: 70, source: 'Portal', url: 'https://exemplo.com/anuncio' }

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('MarketSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ comparaveis: [] }))
    render(<MarketSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando comparáveis')
    expect(await screen.findByText('Nenhum comparável cadastrado')).toBeInTheDocument()
  })

  it('lista comparáveis existentes', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ comparaveis: [comparable] }))
    render(<MarketSection propertyId={5} />)

    expect(await screen.findByText('VENDA')).toBeInTheDocument()
    expect(screen.getByText('70 m²')).toBeInTheDocument()
    expect(screen.getByText('Portal')).toBeInTheDocument()
  })

  it('valida o tipo e cadastra um comparável', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ comparaveis: [] }))
      .mockReturnValueOnce(response(comparable))
    render(<MarketSection propertyId={5} />)
    await screen.findByText('Nenhum comparável cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo comparável' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar comparável' }))
    expect(await screen.findByText('Informe o tipo do comparável.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'VENDA' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar comparável' }))

    expect(await screen.findByText('Comparável cadastrado com sucesso.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[1]
    expect(postCall[0]).toContain('/api/imoveis/5/comparaveis')
    expect(JSON.parse(String((postCall[1] as RequestInit).body)).kind).toBe('VENDA')
  })

  it('exibe erro de cadastro da API', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ comparaveis: [] }))
      .mockReturnValueOnce(response({ detail: 'Dados inválidos' }, false, 422))
    render(<MarketSection propertyId={5} />)
    await screen.findByText('Nenhum comparável cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo comparável' })[0])
    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'VENDA' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar comparável' }))

    expect(await screen.findByText('Dados inválidos')).toBeInTheDocument()
  })

  it('trata erro ao carregar e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(response({ comparaveis: [comparable] }))
    render(<MarketSection propertyId={5} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('VENDA')).toBeInTheDocument())
  })
})
