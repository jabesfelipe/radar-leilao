import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FinancialSection } from './FinancialSection'

const cost = { id: 1, property_id: 5, category: 'IPTU', description: 'IPTU 2026', amount: 1200, recurring: true }
const debt = { id: 2, property_id: 5, category: 'CONDOMINIO', creditor: 'Condomínio Central', amount: 3500, reference_date: '2026-01-01', status: 'PENDENTE', evidence_id: 9 }

const financeBody = {
  property_id: 5,
  analysis_version: null,
  premissas: null,
  financeiro: {
    custo_total: 200000, custo_saida: null, valor_mercado: null,
    resultado_liquido: null, resultado_provisorio: false,
    margem_liquida: null, roi_operacao: null, preco_maximo: null,
    preco_maximo_detalhe: { viavel: false, mensagem: 'Informe a meta e o valor de venda estimado.' },
    cenarios: [], pendencias: ['Meta de preço máximo não configurada; preço máximo não calculado.'],
  },
  historico: [],
}

function jsonResponse(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

// Roteia o mock de fetch por URL (resiliente à ordem das chamadas em Promise.all).
function routeFetch(opts: { custos?: unknown[]; dividas?: unknown[]; finance?: unknown; postBody?: unknown; postOk?: boolean; postStatus?: number }) {
  vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = (init?.method ?? 'GET').toUpperCase()
    if (method === 'POST' || method === 'PUT') {
      return jsonResponse(opts.postBody ?? {}, opts.postOk ?? true, opts.postStatus ?? 200)
    }
    if (url.includes('/custos')) return jsonResponse({ property_id: 5, custos: opts.custos ?? [], historico: [] })
    if (url.includes('/dividas')) return jsonResponse({ property_id: 5, dividas: opts.dividas ?? [], historico: [] })
    if (url.includes('/financeiro')) return jsonResponse(opts.finance ?? financeBody)
    throw new Error(`sem rota para ${url}`)
  })
}

describe('FinancialSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estados vazios de custos e dívidas', async () => {
    routeFetch({})
    render(<FinancialSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando dados financeiros')
    expect(await screen.findByText('Nenhum custo cadastrado')).toBeInTheDocument()
    expect(screen.getByText('Nenhuma dívida cadastrada')).toBeInTheDocument()
  })

  it('carrega custos e dívidas existentes', async () => {
    routeFetch({ custos: [cost], dividas: [debt] })
    render(<FinancialSection propertyId={5} />)

    expect(await screen.findByText('IPTU 2026')).toBeInTheDocument()
    expect(screen.getByText('Recorrente')).toBeInTheDocument()
    expect(screen.getByText('Condomínio Central')).toBeInTheDocument()
    expect(screen.getByText('PENDENTE')).toBeInTheDocument()
    expect(screen.getByText('#9')).toBeInTheDocument()
  })

  it('exibe o painel de premissas e resultado com pendência de preço máximo', async () => {
    routeFetch({})
    render(<FinancialSection propertyId={5} />)

    expect(await screen.findByText('Premissas e resultado')).toBeInTheDocument()
    expect(screen.getByText('Preço máximo indisponível')).toBeInTheDocument()
  })

  it('valida obrigatórios e cadastra um custo', async () => {
    routeFetch({ postBody: cost })
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('Nenhum custo cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo custo' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar custo' }))
    expect(await screen.findByText('Informe a categoria.')).toBeInTheDocument()
    expect(screen.getByText('Informe a descrição.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Categoria'), { target: { value: 'IPTU' } })
    fireEvent.change(screen.getByLabelText('Descrição'), { target: { value: 'IPTU 2026' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar custo' }))

    expect(await screen.findByText('Custo cadastrado com sucesso.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls.find((c) => String(c[0]).includes('/custos') && (c[1] as RequestInit)?.method === 'POST')
    expect(postCall).toBeTruthy()
    expect(JSON.parse(String((postCall![1] as RequestInit).body)).category).toBe('IPTU')
  })

  it('valida obrigatório e cadastra uma dívida', async () => {
    routeFetch({ postBody: debt })
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('Nenhuma dívida cadastrada')

    fireEvent.click(screen.getAllByRole('button', { name: 'Nova dívida' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar dívida' }))
    expect(await screen.findByText('Informe a categoria.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Categoria'), { target: { value: 'CONDOMINIO' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar dívida' }))

    expect(await screen.findByText('Dívida cadastrada com sucesso.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls.find((c) => String(c[0]).includes('/dividas') && (c[1] as RequestInit)?.method === 'POST')
    expect(postCall).toBeTruthy()
    expect(JSON.parse(String((postCall![1] as RequestInit).body)).category).toBe('CONDOMINIO')
  })

  it('sinaliza preço máximo provisório quando há custos materiais desconhecidos', async () => {
    const financeProvisorio = {
      ...financeBody,
      financeiro: {
        ...financeBody.financeiro,
        preco_maximo: 222857,
        preco_maximo_provisorio: true,
        preco_maximo_definitivo: false,
        preco_maximo_detalhe: { provisorio: true, custos_desconhecidos: ['itbi', 'registro'] },
        pendencias: ['Preço máximo é ESTIMATIVA PROVISÓRIA: há custos materiais desconhecidos (itbi, registro).'],
      },
    }
    routeFetch({ finance: financeProvisorio })
    render(<FinancialSection propertyId={5} />)

    expect(await screen.findByText('Preço máximo provisório')).toBeInTheDocument()
    // O texto "estimativa provisória" aparece no rótulo e no alerta; basta haver ocorrência.
    expect(screen.getAllByText(/estimativa provisória/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/O teto real tende a ser menor/i)).toBeInTheDocument()
  })

  it('sinaliza preço máximo definitivo quando as premissas materiais estão completas', async () => {
    const financeDefinitivo = {
      ...financeBody,
      financeiro: {
        ...financeBody.financeiro,
        preco_maximo: 222857,
        preco_maximo_provisorio: false,
        preco_maximo_definitivo: true,
        pendencias: [],
      },
    }
    routeFetch({ finance: financeDefinitivo })
    render(<FinancialSection propertyId={5} />)

    expect(await screen.findByText('Preço máximo definitivo')).toBeInTheDocument()
  })

  it('salva premissas financeiras e recalcula', async () => {
    const financeComPreco = { ...financeBody, financeiro: { ...financeBody.financeiro, preco_maximo: 222857, pendencias: [] } }
    routeFetch({ postBody: financeComPreco })
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('Premissas e resultado')

    fireEvent.change(screen.getByLabelText('Meta financeira'), { target: { value: 'LUCRO_MINIMO' } })
    fireEvent.change(screen.getByLabelText('Meta de lucro (R$)'), { target: { value: '40000' } })
    fireEvent.change(screen.getByLabelText('Valor de venda estimado (R$)'), { target: { value: '320000' } })
    fireEvent.click(screen.getByRole('button', { name: /Salvar premissas/ }))

    expect(await screen.findByText('Premissas financeiras salvas. O resultado foi recalculado.')).toBeInTheDocument()
    const putCall = vi.mocked(fetch).mock.calls.find((c) => String(c[0]).includes('/financeiro/premissas') && (c[1] as RequestInit)?.method === 'PUT')
    expect(putCall).toBeTruthy()
    const body = JSON.parse(String((putCall![1] as RequestInit).body))
    expect(body.goal_kind).toBe('LUCRO_MINIMO')
    expect(body.goal_value).toBe(40000)
    expect(body.valor_venda_estimado).toBe(320000)
  })

  it('exibe erro de cadastro da API', async () => {
    routeFetch({ postBody: { detail: 'Dados inválidos' }, postOk: false, postStatus: 422 })
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('Nenhum custo cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo custo' })[0])
    fireEvent.change(screen.getByLabelText('Categoria'), { target: { value: 'IPTU' } })
    fireEvent.change(screen.getByLabelText('Descrição'), { target: { value: 'IPTU 2026' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar custo' }))

    expect(await screen.findByText('Dados inválidos')).toBeInTheDocument()
  })

  it('trata erro ao carregar e permite tentar novamente', async () => {
    let falhou = false
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/custos') && !falhou) {
        falhou = true
        return jsonResponse({ detail: 'Falha' }, false, 500)
      }
      if (url.includes('/custos')) return jsonResponse({ property_id: 5, custos: [cost], historico: [] })
      if (url.includes('/dividas')) return jsonResponse({ property_id: 5, dividas: [debt], historico: [] })
      if (url.includes('/financeiro')) return jsonResponse(financeBody)
      throw new Error(`sem rota para ${url}`)
    })
    render(<FinancialSection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('IPTU 2026')).toBeInTheDocument())
  })
})
