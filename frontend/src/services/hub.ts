import { PropertiesServiceError } from './properties'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`)
  } catch {
    throw new PropertiesServiceError('Não foi possível conectar ao servidor. Tente novamente.')
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : 'Não foi possível carregar os dados.'
    throw new PropertiesServiceError(detail, response.status)
  }
  return payload as T
}

export type DashboardData = {
  kpis: { imoveis: number; em_analise: number; com_pendencias: number; riscos_altos: number; oportunidades: number }
  pipeline: Record<string, number>
  alertas: Array<{ tipo: string; property_id: number; titulo: string; detalhe: string }>
  recentes: Array<{ id: number; titulo: string; updated_at?: string }>
}

export type PropertySummary = {
  id: number
  titulo: string
  cidade?: string | null
  uf?: string | null
  origem?: string | null
  status?: string | null
  lance?: number | string | null
  avaliacao?: number | string | null
  preco_maximo?: number | string | null
  preco_maximo_definitivo?: boolean
  preco_maximo_provisorio?: boolean
  custo_total?: number | string | null
  break_even?: number | string | null
  roi_operacao?: number | string | null
  margem_liquida?: number | string | null
  pendencias?: number
  riscos_ativos?: number
  risco_alto?: boolean
  correlacao_juridica?: string | null
  processos?: number
  veredito?: string | null
  analysis_version?: number | null
}

export const getDashboard = () => request<DashboardData>('/api/dashboard')
export const getPropertiesSummary = () => request<PropertySummary[]>('/api/imoveis-resumo')
export const getFinancialHub = () => request<{ total: number; itens: PropertySummary[] }>('/api/financeiro')
export const getJuridicalHub = () => request<{ processos: Array<Record<string, unknown>>; total_processos: number; riscos_juridicos: number }>('/api/juridico')
export const getRisksHub = (severity?: string) => request<{ total: number; riscos: Array<Record<string, unknown>> }>(`/api/riscos${severity ? `?severity=${encodeURIComponent(severity)}` : ''}`)
export const getVerdictsHub = () => request<{ total: number; vereditos: Array<Record<string, unknown>> }>('/api/veredito')
export const getMarketHub = () => request<{ total: number; comparaveis: Array<Record<string, unknown>> }>('/api/mercado')
export const getOccupancyHub = () => request<{ total: number; ocupacoes: Array<Record<string, unknown>> }>('/api/ocupacao')
export const getDocumentsHub = (docType?: string) => request<{ total: number; documentos: Array<Record<string, unknown>> }>(`/api/documentos${docType ? `?doc_type=${encodeURIComponent(docType)}` : ''}`)
export const getHistoryHub = () => request<{ total: number; eventos: Array<Record<string, unknown>> }>('/api/historico')
export const getChecklistHub = () => request<{ totais: Record<string, number>; itens: Array<Record<string, unknown>> }>('/api/checklist-global')

export function formatMoney(value?: number | string | null) {
  if (value === undefined || value === null || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n)
}

export function formatPercent(value?: number | string | null) {
  if (value === undefined || value === null || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return `${(n * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}
