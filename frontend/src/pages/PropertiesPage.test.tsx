import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PropertiesPage } from './PropertiesPage'

const property = {
  id: 1,
  title: 'Apartamento Centro',
  address: 'Rua Exemplo, 100',
  city: 'São Paulo',
  state: 'SP',
  property_type: 'Apartamento',
  status: 'EM_ANALISE',
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('PropertiesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([]))
    render(<PropertiesPage />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando imóveis')
    expect(await screen.findByText('Nenhum imóvel cadastrado')).toBeInTheDocument()
  })

  it('renderiza imóveis cadastrados', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([property]))
    render(<PropertiesPage />)

    expect(await screen.findByText('Apartamento Centro')).toBeInTheDocument()
    expect(screen.getByText('Rua Exemplo, 100')).toBeInTheDocument()
    expect(screen.getByText('São Paulo · SP')).toBeInTheDocument()
    expect(screen.getByText('EM ANALISE')).toBeInTheDocument()
  })

  it('abre o detalhe do imóvel ao clicar no card', async () => {
    const onOpenProperty = vi.fn()
    vi.mocked(fetch).mockReturnValueOnce(response([property]))
    render(<PropertiesPage onOpenProperty={onOpenProperty} />)

    fireEvent.click(await screen.findByText('Apartamento Centro'))
    expect(onOpenProperty).toHaveBeenCalledWith(1)
  })

  it('abre o wizard e valida campos obrigatórios da 1ª etapa', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([]))
    render(<PropertiesPage />)
    await screen.findByText('Nenhum imóvel cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo imóvel' })[0])
    expect(screen.getByRole('heading', { name: 'Novo imóvel' })).toBeInTheDocument()
    expect(screen.getByLabelText('Tipo do imóvel')).toHaveValue('Apartamento')

    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))
    expect(await screen.findByText('Informe uma identificação com pelo menos 2 caracteres.')).toBeInTheDocument()
    expect(screen.getByText('Informe a cidade.')).toBeInTheDocument()
    // Não deve ter feito POST ainda (só o GET inicial)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('exibe erro da API ao carregar e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(Promise.reject(new Error('Servidor indisponível')))
      .mockReturnValueOnce(response([property]))
    render(<PropertiesPage />)

    expect(await screen.findByText('Não foi possível conectar ao servidor. Tente novamente.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('Apartamento Centro')).toBeInTheDocument())
  })

  it('não mostra estado vazio de sucesso quando o carregamento falha sem dados', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ detail: 'Erro interno' }, false, 500))
    render(<PropertiesPage />)

    expect(await screen.findByText('Erro interno')).toBeInTheDocument()
    expect(screen.queryByText('Nenhum imóvel cadastrado')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })
})
