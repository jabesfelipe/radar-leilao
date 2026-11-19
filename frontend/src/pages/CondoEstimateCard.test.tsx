import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CondoEstimateCard } from './CondoEstimateCard'

const cenario = (fator: number, meses: number, total: number, comprador: number, caixa: number, fin: number | null) => ({
  meses_em_atraso: meses, fator, principal: total * 0.8, multa: total * 0.02, juros: total * 0.1, correcao: total * 0.08, total,
  divida_potencial: total, responsabilidade_comprador: comprador, responsabilidade_caixa: caixa, valor_no_financeiro: fin,
})
const estimativa = {
  possivel: true, confianca: 'MEDIA', uso_no_financeiro: 'base usa o provável',
  aviso: 'Estimativa calculada com base em informações documentais e premissas configuráveis. Não representa dívida confirmada. Solicite declaração atualizada ao condomínio.',
  cenarios_detalhe: { baixo: cenario(0.15, 4, 2500, 2500, 0, null), provavel: cenario(0.35, 9, 6000, 6000, 0, 6000), alto: cenario(0.7, 17, 25000, 22000, 3000, 22000) },
  regra_venda: { tipo: 'COMPRADOR_ATE_LIMITE_VENDEDOR_EXCEDENTE', limite: 22000, origem: "condições da venda ('condicoes.txt') (trecho literal)" },
  memoria_calculo: { valor_mensal_referencia: 500, origem_valor_mensal: 'INFORMADO', data_aquisicao: '2001-02-01', origem_data_aquisicao: 'matrícula (R-2)',
    data_consolidacao: '2003-04-03', origem_data_consolidacao: 'matrícula (Av-5)', periodo_meses: 26, periodo_considerado_meses: 26, teto_periodo_meses: 60,
    formula: 'meses em atraso = período × fator', nota: 'O período entre a aquisição e a consolidação NÃO prova inadimplência.' },
}

describe('CondoEstimateCard', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('calcula sem registrar e mostra cenários, regra da venda, fórmula e aviso obrigatório', async () => {
    vi.mocked(fetch).mockReturnValue(Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve({ property_id: 5, estimativa, estimativa_id: null }) }) as Promise<Response>)
    render(<CondoEstimateCard propertyId={5} />)
    fireEvent.change(screen.getByLabelText('Condomínio mensal (opcional)'), { target: { value: '500' } })
    fireEvent.click(screen.getByRole('button', { name: 'Calcular pela matrícula' }))
    expect(await screen.findByText(/Não representa dívida confirmada/)).toBeInTheDocument()
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/api/imoveis/5/debitos/estimar-condominio/matricula')
    expect(JSON.parse(String((init as RequestInit).body))).toEqual({ monthly_reference: 500, persist: false })
    expect(screen.getByText('Provável')).toBeInTheDocument()
    expect(screen.getByText('não usado')).toBeInTheDocument()
    expect(screen.getByText(/Regra da venda aplicada depois da estimativa/)).toBeInTheDocument()
    expect(screen.getByText(/NÃO prova inadimplência/)).toBeInTheDocument()
  })

  it('sem dados suficientes mostra o motivo', async () => {
    vi.mocked(fetch).mockReturnValue(Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve({ property_id: 5, estimativa_id: null,
      estimativa: { ...estimativa, possivel: false, motivo: 'Estimativa não calculável: falta data de consolidação.', cenarios_detalhe: undefined } }) }) as Promise<Response>)
    render(<CondoEstimateCard propertyId={5} />)
    fireEvent.click(screen.getByRole('button', { name: 'Registrar estimativa da matrícula' }))
    expect(await screen.findByText(/falta data de consolidação/)).toBeInTheDocument()
  })
})
