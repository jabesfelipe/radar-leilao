import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PropertyDetailPage } from './PropertyDetailPage'

const property = {
  id: 7,
  title: 'Apartamento Centro',
  address: 'Rua Exemplo, 100',
  city: 'São Paulo',
  state: 'SP',
  property_type: 'Apartamento',
  area_m2: 72,
  bedrooms: 2,
  status: 'EM_ANALISE',
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('PropertyDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('carrega e exibe os dados reais do imóvel', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ imovel: property }))
    render(<PropertyDetailPage propertyId={7} onBack={vi.fn()} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando imóvel')
    expect(await screen.findByRole('heading', { name: 'Apartamento Centro' })).toBeInTheDocument()
    expect(screen.getAllByText('Rua Exemplo, 100').length).toBeGreaterThan(0)
    expect(screen.getByText('São Paulo · SP')).toBeInTheDocument()
    expect(screen.getByText('72 m²')).toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/imoveis/7')
  })

  it('mantém a Visão geral como seção inicial e navega entre seções visuais', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ imovel: property }))
    render(<PropertyDetailPage propertyId={7} onBack={vi.fn()} />)
    await screen.findByRole('heading', { name: 'Apartamento Centro' })

    expect(screen.getByRole('button', { name: 'Visão geral' })).toHaveAttribute('aria-current', 'page')
    fireEvent.click(screen.getByRole('button', { name: 'Financeiro' }))
    expect(screen.getByRole('button', { name: 'Financeiro' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText('MÓDULO EM PREPARAÇÃO')).toBeInTheDocument()
  })

  it('trata imóvel inexistente ou erro da API', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ detail: 'Imóvel não encontrado' }, false, 404))
    render(<PropertyDetailPage propertyId={99} onBack={vi.fn()} />)

    expect(await screen.findByText('Imóvel não encontrado')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })

  it('permite voltar para a lista de imóveis', async () => {
    const onBack = vi.fn()
    vi.mocked(fetch).mockReturnValueOnce(response({ imovel: property }))
    render(<PropertyDetailPage propertyId={7} onBack={onBack} />)
    await screen.findByRole('heading', { name: 'Apartamento Centro' })

    fireEvent.click(screen.getByRole('button', { name: 'Voltar para imóveis' }))
    expect(onBack).toHaveBeenCalledOnce()
  })

  it('apresenta todas as seções futuras do dossiê', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ imovel: property }))
    render(<PropertyDetailPage propertyId={7} onBack={vi.fn()} />)
    await screen.findByRole('heading', { name: 'Apartamento Centro' })

    for (const label of ['Visão geral', 'Leilão', 'Documentos', 'Matrícula', 'Edital', 'Processos Jurídicos', 'Financeiro', 'Mercado', 'Ocupação', 'Checklist', 'Riscos', 'Veredito', 'Histórico']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
  })

  it('recarrega ao tentar novamente após erro', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Imóvel não encontrado' }, false, 404))
      .mockReturnValueOnce(response({ imovel: property }))
    render(<PropertyDetailPage propertyId={7} onBack={vi.fn()} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Apartamento Centro' })).toBeInTheDocument())
  })
})
