import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PostAuctionSection } from './PostAuctionSection'

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

const inactiveOverview = {
  property_id: 5,
  ativado: false,
  pos_arrematacao: null,
  etapas: [],
  custos: [],
  contatos: [],
  consultorias: [],
  minutas: [],
  resumo_financeiro: { ativado: false },
  financeiro_analise: {},
}

const activeOverview = {
  property_id: 5,
  ativado: true,
  pos_arrematacao: { id: 1, property_id: 5, status: 'EM_ANDAMENTO', eviction_mode: 'PROPRIA' },
  etapas: [
    { id: 10, property_id: 5, stage_key: 'ARREMATACAO', title: 'Arrematação', sort_order: 1, status: 'PENDENTE' },
  ],
  custos: [
    { id: 20, property_id: 5, category: 'ITBI', planned_amount: 1000, actual_amount: 0, status: 'PENDENTE' },
  ],
  contatos: [],
  consultorias: [],
  minutas: [],
  resumo_financeiro: {
    ativado: true, orcamento_inicial: 50000, valor_venda_estimado: 80000, custo_saida_estimado: 4000,
    previsto_total: 1000, realizado_total: 0,
    pendente_total: 1000, variacao_previsto_realizado: -1000, custo_total_acumulado: 50000,
    lucro_estimado: null, roi_estimado: null, qtd_custos: 1,
  },
  financeiro_analise: {},
}

describe('PostAuctionSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('mostra CTA de ativação quando o fluxo não está ativado', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response(inactiveOverview))
    render(<PostAuctionSection propertyId={5} />)
    expect(await screen.findByText('Fluxo de pós-arrematação não iniciado')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ativar pós-arrematação/ })).toBeInTheDocument()
  })

  it('ativa o fluxo ao clicar no CTA', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response(inactiveOverview))
      .mockReturnValueOnce(response({ ativado: true }))
      .mockReturnValueOnce(response(activeOverview))
    render(<PostAuctionSection propertyId={5} />)
    await screen.findByText('Fluxo de pós-arrematação não iniciado')

    fireEvent.click(screen.getByRole('button', { name: /Ativar pós-arrematação/ }))

    await waitFor(() => {
      const activateCall = vi.mocked(fetch).mock.calls.find(([url]) => String(url).endsWith('/pos-arrematacao/ativar'))
      expect(activateCall).toBeTruthy()
      expect(activateCall?.[1]?.method).toBe('POST')
    })
  })

  it('exibe o resumo financeiro consolidado quando ativado', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response(activeOverview))
    render(<PostAuctionSection propertyId={5} />)
    expect(await screen.findByText('SITUAÇÃO DA EXECUÇÃO')).toBeInTheDocument()
    // resumo separado em orçamento herdado / execução / consolidado
    expect(screen.getByText('Orçamento inicial (custo total da análise)')).toBeInTheDocument()
    expect(screen.getByText('Custo de saída estimado (corretagem/tributo)')).toBeInTheDocument()
    expect(screen.getByText('Total previsto na execução')).toBeInTheDocument()
    expect(screen.getByText('Custo total acumulado (análise + pago)')).toBeInTheDocument()
    // etapa e custo carregados
    expect(screen.getByText('Arrematação')).toBeInTheDocument()
    expect(screen.getByText('ITBI')).toBeInTheDocument()
  })

  it('cria um custo pós-arrematação com previsto/realizado/situação', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response(activeOverview))
      .mockReturnValueOnce(response({ custo: {}, resumo_financeiro: {} }))
      .mockReturnValueOnce(response(activeOverview))
    render(<PostAuctionSection propertyId={5} />)
    await screen.findByText('SITUAÇÃO DA EXECUÇÃO')

    fireEvent.click(screen.getByRole('button', { name: /Novo custo/ }))
    fireEvent.change(screen.getByLabelText('Categoria'), { target: { value: 'REFORMA' } })
    fireEvent.change(screen.getByLabelText('Valor previsto'), { target: { value: '2000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar custo' }))

    await waitFor(() => {
      const postCall = vi.mocked(fetch).mock.calls.find(([url, init]) => String(url).endsWith('/pos-arrematacao/custos') && init?.method === 'POST')
      expect(postCall).toBeTruthy()
      const body = JSON.parse(String(postCall?.[1]?.body))
      expect(body.category).toBe('REFORMA')
      expect(body.planned_amount).toBe(2000)
    })
  })

  it('exibe mensagem de erro quando o carregamento falha', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ detail: 'Falhou' }, false, 500))
    render(<PostAuctionSection propertyId={5} />)
    expect(await screen.findByText('Não foi possível carregar')).toBeInTheDocument()
  })
})
