import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MarketIntelligencePanel } from './MarketIntelligencePanel'

const estimate = (tipo: 'VENDA' | 'ALUGUEL', usados: number) => ({
  tipo, quantidade_usada: usados, quantidade_total: usados + 1, quantidade_anunciada: usados, confianca: usados ? 'MEDIA' : 'SEM_DADOS',
  valor_estimado: usados ? 212000 : null, faixa: usados ? { min: 195000, max: 234000 } : null, faixa_criterio: 'P25–P75', indicativa: false,
  estatisticas_m2: {}, desconto_negociacao: '0.10', avisos: usados ? ['13 de 13 valores são de ANÚNCIO (preço pedido)'] : [],
  comparaveis: usados ? [
    { id: 1, valor: 240000, area_m2: 42, valor_m2: 5714.29, tipo_preco: 'ANUNCIADO', similaridade: 0.87, usado: true, motivo: null, fonte: 'ZAP Imóveis (busca)', url: 'https://exemplo.invalid/busca', consultado_em: '2026-11-16', bairro: 'Eucaliptos' },
    { id: 2, valor: 132970, area_m2: 45, tipo_preco: 'ANUNCIADO', similaridade: 0.95, usado: false, motivo: 'Excluído no cadastro: É o próprio imóvel analisado', fonte: 'ZAP Imóveis (busca)', bairro: 'Estados' },
  ] : [],
})

const body = {
  property_id: 7, data_calculo: '2026-11-16', venda: estimate('VENDA', 13), aluguel: estimate('ALUGUEL', 0),
  liquidez: { classificacao: 'ALTA', confianca: 'MEDIA', justificativa: ['Oferta comparável ampla'], prazo_observacao: 'Sem dados de tempo de venda.' },
  valores: { valor_mercado_estimado: 212000, faixa_venda: { min: 195000, max: 234000 }, aluguel_estimado: null, aluguel_indicativo: false, faixa_aluguel: null,
    preco_m2_anunciado_mediana: 5179, preco_m2_estimado_mediana: 4661, desconto_sobre_avaliacao: 0.3956, desconto_sobre_mercado: 0.3728,
    observacao_descontos: 'Desconto sobre a avaliação da Caixa ≠ desconto sobre o valor de mercado estimado.' },
  custos: [
    { chave: 'aquisicao', descricao: 'Preço de aquisição', valor: 132970.97, status: 'INFORMADO', origem: 'cadastro', valor_conservador: 132970.97, observacao: '', critico: false },
    { chave: 'itbi', descricao: 'ITBI', valor: 3545.64, status: 'ESTIMADO', origem: 'matrícula do imóvel (Av-5)', valor_conservador: 3545.64, observacao: '', critico: false },
    { chave: 'condominio_atraso', descricao: 'Condomínio em atraso', valor: null, status: 'PENDENTE', origem: 'valor da dívida não informado', valor_conservador: 22000, observacao: 'Regra Caixa', critico: false },
  ],
  carregamento_mensal: { valor: 350, origem: 'mediana do condomínio' },
  cenarios: [
    { cenario: 'CONSERVADOR', valor_venda: 195000, prazo_meses: 18, investimento_total: 206000, resultado_liquido: -20000, roi: -0.1, margem_seguranca: -0.05, desconto_sobre_mercado: 0.31, custos_pendentes_nao_incluidos: [] },
    { cenario: 'BASE', valor_venda: 212062.30, prazo_meses: 12, investimento_total: 140716.61, corretagem_venda: 12723.74, tributo_venda: 9423.29, resultado_liquido: 49198.66, roi: 0.3496,
      margem_seguranca: 0.31, desconto_sobre_mercado: 0.37, custos_pendentes_nao_incluidos: ['Condomínio em atraso'],
      composicao: {
        itens: [
          { chave: 'aquisicao', descricao: 'Preço de aquisição', valor: 132970.97, status: 'INFORMADO', incluido: true, base_valor: 'valor confirmado', origem: 'cadastro', dedutivel_ir: true },
          { chave: 'itbi', descricao: 'ITBI', valor: 3545.64, status: 'ESTIMADO', incluido: true, base_valor: 'estimativa', origem: 'matrícula', dedutivel_ir: true },
          { chave: 'manutencao_posse', descricao: 'Condomínio durante a posse (12 meses × R$ 350,00)', valor: 4200, status: 'ESTIMADO', incluido: true, base_valor: 'estimativa', origem: 'carregamento', dedutivel_ir: false },
          { chave: 'condominio_atraso', descricao: 'Condomínio em atraso', valor: null, status: 'PENDENTE', incluido: false, base_valor: null, origem: 'não informado', dedutivel_ir: false },
        ],
        investimento_total: 140716.61, formula: 'resultado = venda líquida − IR − investimento',
        despesas_financeiras: { valor: 0, observacao: 'Compra à vista: financiamento não modelado.' },
        venda_bruta: 212062.30, corretagem_venda: { valor: 12723.74, percentual: 0.06, origem: 'padrão' }, venda_liquida: 199338.56,
        custo_aquisicao_dedutivel_ir: 136516.61, base_ir: 62821.95, ir_ganho_capital: { valor: 9423.29, aliquota: 0.15, origem: 'padrão', observacao: 'Sem isenções.' },
        resultado_liquido: 49198.66, venda_equilibrio: 146600.00,
      } },
  ],
  preco_maximo: { recomendado: null, criterio: 'ROI mínimo de 20% no cenário conservador', provisorio: true },
  premissas: { 'mercado.desconto_negociacao': { valor: '0.10', origem: 'padrão do sistema (parâmetro configurável)', descricao: 'Desconto de negociação sobre preço anunciado' } },
  conclusao: { resultado: 'INCONCLUSIVO', motivos: ['Informações críticas ausentes impedem conclusão favorável.'], bloqueios: ['Situação de ônus e gravames inconclusiva.'] },
}

function jsonResponse(payload: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(payload) }) as Promise<Response>
}

describe('MarketIntelligencePanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('mostra o selo de estimativa preliminar com avaliação, fator e valor', async () => {
    const preliminar = { valor: 187000, avaliacao: 220000, fator: 0.85, fator_origem: 'catálogo de parâmetros (viabilidade.fator_venda_avaliacao)',
      selo: 'Estimativa preliminar', confianca: 'BAIXA', observacao: 'Informe o valor de venda em Financeiro > Premissas.', formula: 'R$ 220.000,00 × 85% = R$ 187.000,00' }
    vi.mocked(fetch).mockImplementation(() => jsonResponse({ ...body, valores: { ...body.valores, venda_preliminar: preliminar } }))
    render(<MarketIntelligencePanel propertyId={7} />)
    expect(await screen.findByText('Estimativa preliminar')).toBeInTheDocument()
    expect(screen.getByText(/Valor de venda preliminar estimado/)).toBeInTheDocument()
    expect(screen.getByText(/Não há comparáveis suficientes/)).toBeInTheDocument()
  })

  it('mostra conclusão, valores, custos por situação, cenários e comparáveis com fonte', async () => {
    vi.mocked(fetch).mockImplementation(() => jsonResponse(body))
    render(<MarketIntelligencePanel propertyId={7} />)
    expect(await screen.findByText('Inconclusivo')).toBeInTheDocument()
    expect(screen.getByText('Situação de ônus e gravames inconclusiva.')).toBeInTheDocument()
    expect(screen.getByText('Valor de mercado estimado')).toBeInTheDocument()
    expect(screen.getAllByText('Estimado').length).toBeGreaterThan(1)       // legenda + custo
    expect(screen.getAllByText('Pendente').length).toBeGreaterThan(1)
    expect(screen.getAllByText('Confirmado').length).toBeGreaterThan(1)
    expect(screen.getByText(/CONSERVADOR/)).toBeInTheDocument()
    expect(screen.getByText(/Excluído: Excluído no cadastro: É o próprio imóvel analisado/)).toBeInTheDocument()
    expect(screen.getAllByText('Anunciado').length).toBeGreaterThan(0)
    expect(screen.getByText(/13 de 13 valores são de ANÚNCIO/)).toBeInTheDocument()
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('/api/imoveis/7/inteligencia-mercado')
    // composição auditável: itens, corretagem, IR e resultado aparecem linha a linha
    expect(screen.getByText('Composição do cenário BASE')).toBeInTheDocument()
    expect(screen.getByText('= Investimento total')).toBeInTheDocument()
    expect(screen.getByText(/− IR sobre ganho de capital/)).toBeInTheDocument()
    expect(screen.getByText('Memória do IR sobre ganho de capital')).toBeInTheDocument()
    expect(screen.getByText('= Resultado líquido')).toBeInTheDocument()
    expect(screen.getByText('Fora da soma (sem valor; não contados como zero)')).toBeInTheDocument()
  })

  it('separa confirmado, reserva e fora da soma; mostra memória do IR do conservador, regra Caixa, teto por cenário e locação', async () => {
    const conservador = {
      cenario: 'CONSERVADOR', valor_venda: 194999.80, prazo_meses: 18, investimento_total: 206451.03, corretagem_venda: 11699.99, tributo_venda: 4912.32,
      resultado_liquido: -28063.54, roi: -0.1359, margem_seguranca: -0.1801, desconto_sobre_mercado: 0.31, completo: false,
      custos_pendentes_nao_incluidos: ['Regularização'],
      premissas: { tratamento_pendencias: ['Condomínio em atraso: teto de responsabilidade do comprador (R$ 22.000,00)', 'Regularização: sem valor, fora da soma'],
        prazo_meses: 18, corretagem_venda: 0.06, ir_ganho_capital: 0.15 },
      composicao: {
        itens: [
          { chave: 'aquisicao', descricao: 'Preço de aquisição', valor: 132970.97, status: 'INFORMADO', incluido: true, base_valor: 'valor confirmado', origem: 'cadastro', dedutivel_ir: true },
          { chave: 'condominio_atraso', descricao: 'Condomínio em atraso', valor: 22000, status: 'PENDENTE', incluido: true, base_valor: 'teto de responsabilidade do comprador (R$ 22.000,00)', origem: 'não informado', dedutivel_ir: false, tipo_valor: 'TETO_CAIXA' },
          { chave: 'regularizacao', descricao: 'Regularização', valor: null, status: 'PENDENTE', incluido: false, base_valor: null, origem: 'não informado', dedutivel_ir: false },
        ],
        investimento_total: 206451.03, formula: 'fórmula', despesas_financeiras: { valor: 0, observacao: 'À vista.' },
        venda_bruta: 194999.80, corretagem_venda: { valor: 11699.99, percentual: 0.06, origem: 'padrão' }, venda_liquida: 183299.81,
        itens_dedutiveis_ir: [{ descricao: 'Preço de aquisição', valor: 132970.97 }, { descricao: 'Reforma', valor: 11375 }],
        itens_nao_dedutiveis_ir: [{ descricao: 'Condomínio em atraso', valor: 22000 }],
        custo_aquisicao_dedutivel_ir: 150551.03, base_ir: 32748.78, ir_ganho_capital: { valor: 4912.32, aliquota: 0.15, origem: 'padrão', observacao: 'Sem isenções.' },
        resultado_liquido: -28063.54, venda_equilibrio: 230123.12,
      },
      rentabilidade_aluguel: { aluguel_mensal: 1092, aluguel_indicativo: true, investimento_base: 200151.03, receita_bruta_anual: 13104, receita_com_vacancia: 11793.60,
        taxa_administracao: 1179.36, condominio_na_vacancia: 420, iptu_na_vacancia: null, resultado_anual_antes_ir: 10194.24, bruta_anual: 0.0655, liquida_anual: 0.0509,
        premissas: 'ocupação 90%', completa: false, pendencias: ['IPTU anual'] },
    }
    const base = { ...body.cenarios[1], completo: false,
      efeito_pendencias_no_teto: { itens: ['Condomínio em atraso: R$ 22.000,00'], valor: 27000, resultado_se_no_teto: 15470.65, resultado_atual: 42470.65, ir_adicional: 0,
        sem_teto_conhecido: ['Regularização'],
        detalhe: [{ chave: 'condominio_atraso', descricao: 'Condomínio em atraso', valor: 22000, dedutivel_ir: false, tipo: 'TETO_CAIXA' as const },
          { chave: 'desocupacao', descricao: 'Desocupação', valor: 5000, dedutivel_ir: false, tipo: 'RESERVA' as const }] } }
    const caixa = { chave: 'tributos_atraso', descricao: 'IPTU e demais tributos em atraso', valor: 0, status: 'INFORMADO', origem: 'dívida cadastrada', valor_conservador: 0,
      valor_base: 0, observacao: '', critico: false, divida_total: 30000, responsabilidade_comprador: 0, assumido_caixa: 30000, limite_responsabilidade: 22000, regra: 'Regra Caixa',
      premissa_conservadora: 'Premissa conservadora: dívida igual ao limite é do comprador' }
    const iptu = { chave: 'iptu_posse', descricao: 'IPTU durante a posse', valor: null, status: 'PENDENTE', origem: 'reserva manual: carnê', valor_conservador: 900,
      valor_base: 600, observacao: '', critico: false, valores_anuais: true, reserva_manual: true, tratamento_base: 'reserva manual de R$ 600,00 por ano (carnê)' }
    const rich = {
      ...body, venda: { ...body.venda, limitacoes: ['10 de 13 comparável(is) sem base de área declarada no anúncio'] },
      custos: [...body.custos, caixa, iptu], cenarios: [{ ...conservador, impacto_reservas: [
        { chave: 'regularizacao', descricao: 'Regularização', reserva: 3000, base_valor: 'reserva manual de R$ 3.000,00 (despachante)', tipo: 'reserva manual',
          efeito_investimento: 3000, efeito_resultado: -3000, efeito_roi: -0.0151, efeito_preco_maximo: -2700.5 }] }, base],
      preco_maximo: { ...body.preco_maximo, por_cenario: {
        CONSERVADOR: { cenario: 'CONSERVADOR', preco_maximo: 68214.91, definitivo: false, provisorio: true, razao: 'PROVISORIO', pendencias: ['Teto provisório.'], roi_no_teto: 0.2 },
        BASE: { cenario: 'BASE', preco_maximo: 144816.84, definitivo: false, provisorio: true, razao: 'PROVISORIO', pendencias: [], roi_no_teto: 0.2,
          com_pendencias_no_teto: { preco_maximo: 89988.20, roi_no_teto: 0.2, itens: ['Condomínio em atraso', 'Desocupação'], sem_teto_conhecido: [] } },
        OTIMISTA: { cenario: 'OTIMISTA', preco_maximo: 161939.94, definitivo: false, provisorio: true, razao: 'PROVISORIO', pendencias: [], roi_no_teto: 0.2 } } },
      conclusao: { ...body.conclusao, ressalvas: ['Aluguel apenas indicativo'] },
    }
    vi.mocked(fetch).mockImplementation(() => jsonResponse(rich))
    render(<MarketIntelligencePanel propertyId={7} />)
    expect(await screen.findByText('Ressalva: Aluguel apenas indicativo')).toBeInTheDocument()
    expect(screen.getByText(/sem base de área declarada/)).toBeInTheDocument()
    expect(screen.getAllByText('Incompleto').length).toBe(2)
    expect(screen.getAllByText('Memória do IR sobre ganho de capital').length).toBe(2)   // conservador e base
    expect(screen.getByText('Custo dedutível: Reforma')).toBeInTheDocument()
    expect(screen.getByText(/Não reduzem a base do IR: Condomínio em atraso/)).toBeInTheDocument()
    expect(screen.getByText(/Assumido pela Caixa: R\$\s?30\.000,00/)).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Preço máximo por cenário' })).toHaveTextContent('OTIMISTA')
    expect(screen.getAllByText('20,0%').length).toBe(3)
    const pend = screen.getByRole('table', { name: 'Pendências no teto' })
    expect(pend).toHaveTextContent('Desocupação')                       // nenhum item somado fica implícito
    expect(pend).toHaveTextContent('teto de responsabilidade Caixa')
    expect(pend).toHaveTextContent('= Resultado com os itens no teto')
    expect(screen.getByText(/Continuam fora da soma, sem teto conhecido: Regularização/)).toBeInTheDocument()
    const tetos = screen.getByRole('table', { name: 'Preço máximo por cenário' })
    expect(tetos).toHaveTextContent('Provisório: não use como lance')
    expect(tetos).toHaveTextContent(/89\.988,20/)
    expect(screen.getByText('Teto Caixa (dívida pendente)')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Locação CONSERVADOR' })).toHaveTextContent('Condomínio nos meses vagos')
    expect(screen.getByText(/aluguel INDICATIVO/)).toBeInTheDocument()
    expect(screen.getByText(/Premissa conservadora: dívida igual ao limite é do comprador/)).toBeInTheDocument()
    expect(screen.getByText(/R\$\s?600,00\/ano/)).toBeInTheDocument()
    const impacto = screen.getByRole('table', { name: 'Impacto das reservas CONSERVADOR' })
    expect(impacto).toHaveTextContent('reserva manual')
    expect(impacto).toHaveTextContent('-1,51 p.p.')
  })

  it('não renderiza nada quando a resposta não é de inteligência de mercado', async () => {
    vi.mocked(fetch).mockImplementation(() => jsonResponse({ property_id: 7, mercado: {} }))
    const { container } = render(<MarketIntelligencePanel propertyId={7} />)
    await new Promise((r) => setTimeout(r, 0))
    expect(container).toBeEmptyDOMElement()
  })

  it('mostra erro e permite tentar novamente', async () => {
    vi.mocked(fetch).mockImplementation(() => jsonResponse({ detail: 'Falha no cálculo' }, false, 500))
    render(<MarketIntelligencePanel propertyId={7} />)
    expect(await screen.findByText('Falha no cálculo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Recarregar inteligência de mercado/ })).toBeInTheDocument()
  })
})
