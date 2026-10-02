import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OccupancySection } from './OccupancySection'

const occupancy = {
  id: 3,
  property_id: 5,
  status: 'OCUPADO' as const,
  occupant_profile: 'Antigo proprietário',
  estimated_cost: 5000,
  estimated_months: 6,
  evidence_id: 12,
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function occupancyResponse(current: unknown) {
  return response({ property_id: 5, situacao_atual: current, ultimo_registro: current, historico: current ? [current] : [] })
}

describe('OccupancySection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(occupancyResponse(null))
    render(<OccupancySection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando ocupação')
    expect(await screen.findByText('Nenhuma ocupação registrada')).toBeInTheDocument()
  })

  it('exibe a ocupação atual existente', async () => {
    vi.mocked(fetch).mockReturnValueOnce(occupancyResponse(occupancy))
    render(<OccupancySection propertyId={5} />)

    expect(await screen.findByText('SITUAÇÃO ATUAL')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'OCUPADO' })).toBeInTheDocument()
    expect(screen.getByText('Antigo proprietário')).toBeInTheDocument()
    expect(screen.getByText('#12')).toBeInTheDocument()
  })

  it('registra ocupação respeitando os status do backend', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(occupancyResponse(null))
      .mockReturnValueOnce(response(occupancy))
      .mockReturnValueOnce(occupancyResponse(occupancy))
    render(<OccupancySection propertyId={5} />)
    await screen.findByText('Nenhuma ocupação registrada')

    fireEvent.click(screen.getAllByRole('button', { name: 'Atualizar situação' })[0])
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'OCUPADO' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar ocupação' }))

    // TASK 75.2: a atualização cria nova avaliação e preserva o histórico.
    expect(await screen.findByText(/nova avaliação de ocupação registrada/i)).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[1]
    expect(postCall[0]).toContain('/api/imoveis/5/ocupacao')
    expect(JSON.parse(String((postCall[1] as RequestInit).body)).status).toBe('OCUPADO')
    expect(screen.getByRole('heading', { name: 'OCUPADO' })).toBeInTheDocument()
  })

  it('exibe erro ao registrar', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(occupancyResponse(null))
      .mockReturnValueOnce(response({ detail: 'Dados inválidos' }, false, 422))
    render(<OccupancySection propertyId={5} />)
    await screen.findByText('Nenhuma ocupação registrada')

    fireEvent.click(screen.getAllByRole('button', { name: 'Atualizar situação' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar ocupação' }))

    expect(await screen.findByText('Dados inválidos')).toBeInTheDocument()
  })

  it('mostra o histórico preservado de avaliações de ocupação', async () => {
    const anterior = { ...occupancy, id: 2, status: 'DESCONHECIDO' as const, created_at: '2026-01-01T10:00:00Z' }
    const atual = { ...occupancy, id: 3, created_at: '2026-02-01T10:00:00Z' }
    vi.mocked(fetch).mockReturnValueOnce(response({ property_id: 5, situacao_atual: atual, ultimo_registro: atual, historico: [anterior, atual] }))
    render(<OccupancySection propertyId={5} />)
    expect(await screen.findByText(/Histórico de avaliações de ocupação/)).toBeInTheDocument()
  })

  it('trata erro ao carregar e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(occupancyResponse(occupancy))
    render(<OccupancySection propertyId={5} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'OCUPADO' })).toBeInTheDocument())
  })
})
