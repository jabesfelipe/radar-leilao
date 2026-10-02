import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DashboardHub, FinancialHub, RisksHub } from './hubs'

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('Hubs globais', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('Dashboard mostra KPIs e alerta navegável', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({
      kpis: { imoveis: 3, em_analise: 2, com_pendencias: 1, riscos_altos: 1, oportunidades: 0 },
      pipeline: { cadastrado: 3, com_veredito: 1 },
      alertas: [{ tipo: 'RISCO_ALTO', property_id: 7, titulo: 'Imóvel 7', detalhe: '1 risco(s) ativo(s)' }],
      recentes: [],
    }))
    const onOpen = vi.fn()
    render(<DashboardHub onOpenProperty={onOpen} />)
    expect(await screen.findByText('Imóveis no Radar')).toBeInTheDocument()
    expect(screen.getByText('Riscos altos')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Imóvel 7'))
    expect(onOpen).toHaveBeenCalledWith(7)
  })

  it('Financeiro lista imóveis com break-even e navega ao imóvel', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({
      total: 1,
      itens: [{ id: 5, titulo: 'Casa A', cidade: 'SP', uf: 'SP', lance: 100000, preco_maximo: 120000, custo_total: 110000, break_even: 115000, roi_operacao: 0.1, risco_alto: false, riscos_ativos: 0, veredito: 'FAVORAVEL' }],
    }))
    const onOpen = vi.fn()
    render(<FinancialHub onOpenProperty={onOpen} />)
    expect(await screen.findByText('Casa A')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Casa A'))
    expect(onOpen).toHaveBeenCalledWith(5)
  })

  it('Riscos mostra estado vazio e permite filtrar', async () => {
    vi.mocked(fetch).mockReturnValue(response({ total: 0, riscos: [] }))
    render(<RisksHub onOpenProperty={vi.fn()} />)
    expect(await screen.findByText('Nenhum risco')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'ALTA' })).toBeInTheDocument()
  })
})
