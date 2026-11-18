import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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

  // TASK 75.2: edição e exclusão de custo (recalcula financeiro, sem nova análise).
  it('edita um custo e recalcula o financeiro', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method ?? 'GET').toUpperCase()
      if (method === 'PATCH' && /\/custos\/1$/.test(url)) {
        return jsonResponse({ custo: { ...cost, amount: 1500 }, financeiro: financeBody.financeiro })
      }
      if (url.includes('/custos')) return jsonResponse({ property_id: 5, custos: [cost], historico: [] })
      if (url.includes('/dividas')) return jsonResponse({ property_id: 5, dividas: [], historico: [] })
      if (url.includes('/financeiro')) return jsonResponse(financeBody)
      throw new Error(`sem rota para ${url}`)
    })
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('IPTU 2026')
    fireEvent.click(screen.getByRole('button', { name: /Editar/ }))
    fireEvent.change(screen.getByLabelText('Valor (opcional)'), { target: { value: '1500' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
    expect(await screen.findByText(/Custo atualizado/)).toBeInTheDocument()
    const patchCall = vi.mocked(fetch).mock.calls.find((c) => /\/custos\/1$/.test(String(c[0])) && (c[1] as RequestInit)?.method === 'PATCH')
    expect(patchCall).toBeTruthy()
  })

  it('exclui um custo após confirmação', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method ?? 'GET').toUpperCase()
      if (method === 'DELETE' && /\/custos\/1$/.test(url)) {
        return jsonResponse({ removido: 1, financeiro: financeBody.financeiro })
      }
      if (url.includes('/custos')) return jsonResponse({ property_id: 5, custos: [cost], historico: [] })
      if (url.includes('/dividas')) return jsonResponse({ property_id: 5, dividas: [], historico: [] })
      if (url.includes('/financeiro')) return jsonResponse(financeBody)
      throw new Error(`sem rota para ${url}`)
    })
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('IPTU 2026')
    fireEvent.click(screen.getByRole('button', { name: /Excluir/ }))
    expect(await screen.findByText(/Custo excluído/)).toBeInTheDocument()
    const delCall = vi.mocked(fetch).mock.calls.find((c) => /\/custos\/1$/.test(String(c[0])) && (c[1] as RequestInit)?.method === 'DELETE')
    expect(delCall).toBeTruthy()
  })
})

// v2: inteligência de mercado → premissas como sugestão editável (nada aplicado sem clique; meta nunca sugerida).
const premissasSalvas = {
  corretagem_pct: '0.05', tax_base: 'GANHO', itbi_aliquota: '0.025', itbi_base_minima: '141825.75', itbi_origem: 'matrícula (Av-5)',
  condicoes_caixa: { condominio_limite_pct_avaliacao: '0.10', tributos_limite_pct_avaliacao: '0.10', origem: 'condições da venda direta Caixa' },
}
const intel = {
  valores: { valor_mercado_estimado: '212062.30', faixa_venda: { min: '190000', max: '230000' }, aluguel_estimado: null, aluguel_indicativo: true, faixa_aluguel: null },
  venda: { tipo: 'VENDA', quantidade_usada: 13, quantidade_total: 20, quantidade_anunciada: 13, confianca: 'MEDIA', desconto_negociacao: '0.10',
    limitacoes: ['Nenhum negócio fechado: só preços ANUNCIADOS.'], estatisticas_m2: {}, comparaveis: [], avisos: [] },
  carregamento_mensal: { valor: null, origem: null },
  premissas: {
    'venda.corretagem_pct': { valor: '0.06', origem: 'padrão declarado do motor', descricao: 'Corretagem' },
    'venda.tributo_ganho_pct': { valor: '0.15', origem: 'padrão declarado do motor', descricao: 'IR' },
    'venda.prazo_meses': { valor: 12, origem: 'padrão declarado do motor', descricao: 'Prazo' },
  },
}

function routeComMercado(mercado: unknown | null) {
  vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = (init?.method ?? 'GET').toUpperCase()
    if (method === 'PUT') return jsonResponse({ ...financeBody, premissas: JSON.parse(String(init?.body)) })
    if (url.includes('/inteligencia-mercado')) return mercado ? jsonResponse(mercado) : jsonResponse({ detail: 'falha' }, false, 500)
    if (url.includes('/custos')) return jsonResponse({ property_id: 5, custos: [], historico: [] })
    if (url.includes('/dividas')) return jsonResponse({ property_id: 5, dividas: [], historico: [] })
    if (url.includes('/financeiro')) return jsonResponse({ ...financeBody, premissas: premissasSalvas })
    throw new Error(`sem rota para ${url}`)
  })
}

describe('FinancialSection: sugestões da inteligência de mercado', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('mostra as sugestões com origem e não preenche nada sem clique', async () => {
    routeComMercado(intel)
    render(<FinancialSection propertyId={5} />)
    const tabela = await screen.findByRole('table', { name: 'Sugestões editáveis' })
    expect(within(tabela).getByRole('row', { name: /Valor de venda estimado/ })).toHaveTextContent('13 comparáveis, confiança MEDIA')
    expect(screen.getByText(/13 de 20 comparáveis usados · 13 com preço ANUNCIADO/)).toBeInTheDocument()
    expect(screen.getByText('Nenhum negócio fechado: só preços ANUNCIADOS.')).toBeInTheDocument()
    // nada aplicado sozinho; o valor do usuário (5%) permanece
    expect(screen.getByLabelText('Valor de venda estimado (R$)')).toHaveValue(null)
    expect(screen.getByLabelText('Corretagem na venda (%)')).toHaveValue(5)
    expect(within(within(tabela).getByRole('row', { name: /Corretagem na venda/ })).getByRole('button')).toHaveTextContent('Substituir pelo sugerido')
    // meta financeira nunca é sugerida; carregamento sem dado também não
    expect(within(tabela).queryByRole('row', { name: /Meta/ })).not.toBeInTheDocument()
    expect(within(tabela).queryByRole('row', { name: /Carregamento/ })).not.toBeInTheDocument()
    expect(screen.getByText(/A meta financeira é decisão do investidor: não há sugestão/)).toBeInTheDocument()
    expect(screen.getByText('Premissas essenciais pendentes')).toBeInTheDocument()
  })

  it('aplica a sugestão só no clique e preserva as premissas v1.0.8 ao salvar', async () => {
    routeComMercado(intel)
    render(<FinancialSection propertyId={5} />)
    const tabela = await screen.findByRole('table', { name: 'Sugestões editáveis' })
    fireEvent.click(within(within(tabela).getByRole('row', { name: /Valor de venda estimado/ })).getByRole('button', { name: 'Usar sugestão' }))
    expect(screen.getByLabelText('Valor de venda estimado (R$)')).toHaveValue(212062.3)
    expect(within(within(tabela).getByRole('row', { name: /Valor de venda estimado/ })).getByText('Em uso')).toBeInTheDocument()
    expect(screen.getByLabelText('Corretagem na venda (%)')).toHaveValue(5)        // outro campo não muda

    fireEvent.click(screen.getByRole('button', { name: /Salvar premissas/ }))
    expect(await screen.findByText('Premissas financeiras salvas. O resultado foi recalculado.')).toBeInTheDocument()
    const put = vi.mocked(fetch).mock.calls.find((c) => String(c[0]).includes('/financeiro/premissas') && (c[1] as RequestInit)?.method === 'PUT')
    const body = JSON.parse(String((put![1] as RequestInit).body))
    expect(body.valor_venda_estimado).toBe(212062.3)
    expect(body.corretagem_pct).toBe(0.05)
    expect(body.goal_kind).toBeNull()                                               // meta continua decisão do usuário
    expect(body.itbi_aliquota).toBe('0.025')
    expect(body.condicoes_caixa).toEqual(premissasSalvas.condicoes_caixa)
  })

  it('sem inteligência de mercado o formulário segue manual, sem sugestão', async () => {
    routeComMercado(null)
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('Premissas e resultado')
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some((c) => String(c[0]).includes('/inteligencia-mercado'))).toBe(true))
    expect(screen.queryByRole('table', { name: 'Sugestões editáveis' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Valor de venda estimado (R$)')).toHaveValue(null)
  })

  it('mostra a composição dos custos com a natureza de cada valor e o pendente fora da soma', async () => {
    const composicao = [
      { chave: 'aquisicao', descricao: 'Preço de aquisição', valor: 132970.97, incluido: true, natureza: 'CONFIRMADO', origem: 'cadastro do leilão/venda' },
      { chave: 'itbi', descricao: 'ITBI', valor: 3545.64, incluido: true, natureza: 'ESTIMADO', origem: 'matrícula (Av-5)' },
      { chave: 'certidoes', descricao: 'Certidões', valor: 600, incluido: true, natureza: 'RESERVA', origem: 'não informado', base_valor: 'reserva de R$ 600,00' },
      { chave: 'regularizacao', descricao: 'Regularização', valor: null, incluido: false, natureza: 'PENDENTE', origem: 'não informado' },
    ]
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/inteligencia-mercado')) return jsonResponse({ detail: 'x' }, false, 500)
      if (url.includes('/custos')) return jsonResponse({ property_id: 5, custos: [], historico: [] })
      if (url.includes('/dividas')) return jsonResponse({ property_id: 5, dividas: [], historico: [] })
      return jsonResponse({ ...financeBody, financeiro: { ...financeBody.financeiro, composicao_custos: composicao } })
    })
    render(<FinancialSection propertyId={5} />)
    const tabela = await screen.findByRole('table', { name: 'Composição dos custos' })
    expect(within(within(tabela).getByRole('row', { name: /ITBI/ })).getByText('Estimado')).toBeInTheDocument()
    expect(within(within(tabela).getByRole('row', { name: /Certidões/ })).getByText('Pendente (reserva)')).toBeInTheDocument()
    expect(within(tabela).getByText('reserva de R$ 600,00')).toBeInTheDocument()
    const pendente = within(tabela).getByRole('row', { name: /Regularização/ })
    expect(within(pendente).getByText('fora da soma')).toBeInTheDocument()
    expect(within(pendente).getByText('Pendente (fora da soma)')).toBeInTheDocument()
  })

  it('sem estimativa de mercado não sugere valor de venda e explica o impacto', async () => {
    routeComMercado({ ...intel, valores: { ...intel.valores, valor_mercado_estimado: null, faixa_venda: null } })
    render(<FinancialSection propertyId={5} />)
    expect(await screen.findByText('Sem estimativa de mercado')).toBeInTheDocument()
    const tabela = screen.getByRole('table', { name: 'Sugestões editáveis' })
    expect(within(tabela).queryByRole('row', { name: /Valor de venda estimado/ })).not.toBeInTheDocument()
  })
})
