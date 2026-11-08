import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { DebtsSection } from './DebtsSection'

function ok(body: unknown, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

const debts = {
  property_id: 5,
  debitos: [],
  legado_debts: [],
  consolidacao: {
    property_id: 5,
    totais: { confirmados: 1000, informados: 500, estimados: 0, despesas_previstas: 0, nao_apurados: 0 },
    contagens: { confirmados: 1, informados: 1, estimados: 0, despesas_previstas: 0, nao_apurados: 0 },
    exposicao_passivo_com_ressalva: 1500,
    ressalvas: ['Estimativas não entram como passivo confirmado.'],
  },
}

const consultas = {
  property_id: 5,
  consultas: [{ id: 1, debt_type_code: 'IPTU', municipality_id: 1, provider: 'manual_assistida', mode: 'ASSISTIDA', status: 'REQUER_INTERVENCAO_MANUAL', attempts: 1, message: 'Aguardando operador.' }],
}

function routeFetch() {
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/debitos/consultas')) return ok(consultas)
    if (url.includes('/debitos/estimar-condominio')) return ok({ property_id: 5, estimativa: { possivel: true, cenarios: { conservador: 13200, provavel: 12000, otimista: 8400 }, confianca: 'MEDIA', memoria_calculo: {}, parametros_usados: [], ressalva: 'Valor ESTIMADO; não comprova dívida.' }, alertas_idade: { nivel: 'ATENCAO', conclusivo: true, mensagem: 'Imóvel com 12 anos.', limites: { nivel_1_anos: 10, nivel_2_anos: 15 } }, estimativa_id: null })
    if (url.includes('/debitos')) return ok(debts)
    return ok({})
  }) as unknown as typeof fetch
}

describe('DebtsSection', () => {
  beforeEach(() => { vi.restoreAllMocks(); routeFetch() })

  it('mostra a consolidação por natureza e a exposição de passivo', async () => {
    render(<DebtsSection propertyId={5} />)
    expect(await screen.findByText('CONSOLIDAÇÃO POR NATUREZA')).toBeInTheDocument()
    expect(screen.getByText('Confirmados')).toBeInTheDocument()
    expect(screen.getByText(/Estimativas não entram como passivo confirmado/i)).toBeInTheDocument()
  })

  it('lista o histórico de consultas com o status padronizado', async () => {
    render(<DebtsSection propertyId={5} />)
    expect(await screen.findByText('REQUER_INTERVENCAO_MANUAL')).toBeInTheDocument()
  })

  it('calcula a estimativa condominial com 3 cenários e ressalva', async () => {
    render(<DebtsSection propertyId={5} />)
    await screen.findByText('CONSOLIDAÇÃO POR NATUREZA')
    fireEvent.click(screen.getByRole('button', { name: 'Calcular estimativa' }))
    await waitFor(() => expect(screen.getByText(/Valor ESTIMADO/i)).toBeInTheDocument())
    expect(screen.getByText('Conservador')).toBeInTheDocument()
  })
})
