import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InvestmentSummarySection } from './InvestmentSummarySection'

const unknown = { valor: null, tipo: 'DESCONHECIDO', tipo_label: 'Desconhecido', origem: 'não levantado' }
const block = {
  qualidade: { nivel: 'INSUFICIENTE', label: 'Amostra insuficiente', quantidade: 0, minimo_recomendado: 7, texto: '0 comparável(is) utilizável(is).' },
  quantidade_usada: 0, quantidade_total: 0, valor_estimado: null, faixa: null, m2_media: null, m2_mediana: null, media_total: null, mediana_total: null,
  comparaveis: [], avisos: [],
}
const summary = {
  property_id: 7,
  recomendacao: { codigo: 'ATENCAO_INVESTIGAR', label: 'ATENÇÃO — INVESTIGAR', arrematar: 'Ainda não: investigue os pontos abaixo antes de dar lance.',
    motivos: ['Confirmado: Imóvel ocupado.', 'Falta: IPTU (pendente de consulta).'], aviso_margem: 'A margem estimada é positiva, mas não basta: há riscos ativos.' },
  numeros: {
    lance: { valor: 132970.97, tipo: 'FATO', tipo_label: 'Fato', origem: 'edital' },
    preco_maximo: { ...unknown, provisorio: true }, valor_venda: { ...unknown, texto: 'AMOSTRA INSUFICIENTE: valor de venda desconhecido.' },
    lucro_estimado: unknown, roi: unknown, margem: unknown, investimento_total: unknown,
  },
  principal_risco: 'Imóvel ocupado',
  pendencias: ['valor de venda (amostra de comparáveis insuficiente)', 'IPTU (pendente de consulta)'],
  proximas_acoes: [{ prioridade: 1, tema: 'Imóvel ocupado', acao: 'Confirmar quem ocupa o imóvel.' }],
  iptu: { status: 'PENDENTE_CONSULTA', status_label: 'Pendente de consulta', texto: 'IPTU ainda não consultado.', automatico: false,
    motivo_sem_automacao: 'Portal exige CPF/CNPJ.', portal: { urls: ['https://prefeitura.exemplo'], exigencias: [], passos: [] }, dados_necessarios: [],
    debito_em_aberto: unknown, sem_debito: false, valor_anual: unknown, aviso: 'Desconhecido nunca é zero.' },
  condominio: { taxa_mensal: { ...unknown, status: 'DESCONHECIDO', status_label: 'Desconhecido' }, estimativa_insuficiente: true,
    texto: 'Estimativa insuficiente: nenhum imóvel parecido com condomínio informado.', referencias: null, confianca: 'SEM_DADOS', mesmo_predio: null,
    divida_acumulada: { valor: null, valor_base: 3000, valor_conservador: 6000, origem: 'estimativa pela matrícula', tipo: 'ESTIMATIVA', tipo_label: 'Estimativa' },
    taxa_extra: { status: 'DESCONHECIDO', texto: 'Taxa extra: sem fonte automática.' },
    busca_automatica: { status: 'NAO_CONFIGURADO', texto: 'Busca automática não configurada.' }, aviso: 'Taxa mensal e dívida acumulada são valores diferentes.' },
  mercado: { venda: block, aluguel: block, valor_venda_usado: unknown, aluguel_estimado: unknown,
    yield_bruto_anual: { sobre_valor_mercado: null, sobre_aquisicao: null, texto: 'Yield não calculado.' }, liquidez: null,
    busca_automatica: { status: 'NAO_CONFIGURADO', texto: 'Busca automática de anúncios não configurada.' } },
  financeiro: { confirmado: [], estimado: [{ chave: 'desocupacao', descricao: 'Desocupação', valor: null, valor_base: 5000, valor_conservador: 5000, origem: 'reserva' }],
    desconhecido: [{ chave: 'reforma', descricao: 'Reforma', valor: null, valor_base: null, valor_conservador: null, motivo: 'sem valor: fora da soma (não é zero)' }],
    nao_incluido: [], texto: 'Confirmado, estimado, desconhecido e não incluído.' },
  riscos: { itens: [] },
}

describe('InvestmentSummarySection', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('responde arrematar?, mostra o tipo de cada número e separa taxa de condomínio da dívida', async () => {
    vi.mocked(fetch).mockReturnValueOnce(Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(summary) }) as Promise<Response>)
    render(<InvestmentSummarySection propertyId={7} />)

    expect(await screen.findByText('ATENÇÃO — INVESTIGAR')).toBeInTheDocument()
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('/api/imoveis/7/resumo-investimento')
    expect(screen.getByText('Ainda não: investigue os pontos abaixo antes de dar lance.')).toBeInTheDocument()
    expect(screen.getByText(/A margem estimada é positiva/)).toBeInTheDocument()
    expect(screen.getByText('AMOSTRA INSUFICIENTE: valor de venda desconhecido.')).toBeInTheDocument()
    expect(screen.getAllByText('Fato').length).toBeGreaterThan(0)
    expect(screen.getByText('Pendente de consulta')).toBeInTheDocument()
    expect(screen.getByText(/Estimativa insuficiente/)).toBeInTheDocument()
    expect(screen.getByText(/R\$\s?3\.000,00 a R\$\s?6\.000,00/)).toBeInTheDocument()
    expect(screen.getByText('Busca automática de anúncios não configurada.')).toBeInTheDocument()
    expect(screen.getByText('Desconhecido (fora da soma) (1)')).toBeInTheDocument()
    expect(screen.getByText('Confirmar quem ocupa o imóvel.', { exact: false })).toBeInTheDocument()
  })

  it('mostra erro com nova tentativa', async () => {
    vi.mocked(fetch).mockReturnValueOnce(Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ detail: 'Falha' }) }) as Promise<Response>)
    render(<InvestmentSummarySection propertyId={7} />)
    expect(await screen.findByText('Falha')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Tentar novamente/ })).toBeInTheDocument()
  })
})
