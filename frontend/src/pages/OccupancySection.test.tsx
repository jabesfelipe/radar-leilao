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

  it('possíveis ocupantes: aviso obrigatório, origem e trecho, carregados sob demanda', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(occupancyResponse(null))
      .mockReturnValueOnce(response({
        property_id: 5, fonte: 'matrícula anexada', motivo: null, situacao_registrada: null,
        aviso: 'Estas pessoas foram identificadas nos documentos do imóvel. Esta informação é apenas uma sugestão e não confirma ocupação atual.',
        observacao: 'O checklist (itens 11 e 27) e o financeiro usam só o registro de ocupação confirmado pelo usuário.',
        possiveis_ocupantes: [{ nome: 'COMPRADOR TESTE FICTÍCIO', papeis: ['Comprador'],
          origens: [{ documento: 'matricula.txt', ato: 'R-2', tipo_ato: 'Compra e venda', data: '2001-02-01', papel: 'Comprador', como_identificado: 'texto', trecho: 'vendeu a COMPRADOR TESTE FICTÍCIO' }] }],
      }))
    render(<OccupancySection propertyId={5} />)
    await screen.findByText('Nenhuma ocupação registrada')
    fireEvent.click(screen.getByRole('button', { name: 'Ver possíveis ocupantes' }))
    expect(await screen.findByText(/apenas uma sugestão e não confirma ocupação atual/)).toBeInTheDocument()
    expect(screen.getByText('COMPRADOR TESTE FICTÍCIO')).toBeInTheDocument()
    expect(screen.getByText(/matricula\.txt · R-2/)).toBeInTheDocument()
    expect(String(vi.mocked(fetch).mock.calls[1][0])).toContain('/api/imoveis/5/ocupacao/possiveis-ocupantes')
  })

  it('envia a verificação (fonte, data, responsável, observação) junto com o status', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(occupancyResponse(null))
      .mockReturnValueOnce(response(occupancy))
      .mockReturnValueOnce(occupancyResponse(occupancy))
    render(<OccupancySection propertyId={5} />)
    await screen.findByText('Nenhuma ocupação registrada')
    fireEvent.click(screen.getAllByRole('button', { name: 'Atualizar situação' })[0])
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'OCUPADO_TERCEIROS' } })
    fireEvent.change(screen.getByLabelText('Fonte da verificação (opcional)'), { target: { value: 'portaria' } })
    fireEvent.change(screen.getByLabelText('Responsável pela verificação (opcional)'), { target: { value: 'Analista' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar ocupação' }))
    await screen.findByText(/nova avaliação de ocupação registrada/i)
    const body = JSON.parse(String((vi.mocked(fetch).mock.calls[1][1] as RequestInit).body))
    expect(body.status).toBe('OCUPADO_TERCEIROS')
    expect(body.verificacao).toEqual({ fonte: 'portaria', responsavel: 'Analista' })
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
