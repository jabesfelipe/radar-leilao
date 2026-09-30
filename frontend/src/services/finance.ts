import { PropertiesServiceError } from './properties'

export type Cost = {
  id: number
  property_id: number
  category: string
  description: string
  amount?: number | string
  recurring?: boolean
  created_at?: string
}

export type CostCreate = {
  category: string
  description: string
  amount?: number
  recurring?: boolean
}

export type Debt = {
  id: number
  property_id: number
  category: string
  creditor?: string
  amount?: number | string
  reference_date?: string | null
  status?: string
  evidence_id?: number | null
  created_at?: string
}

export type DebtCreate = {
  category: string
  creditor?: string
  amount?: number
  reference_date?: string
  status?: string
  evidence_id?: number
}

export type CostsResponse = {
  property_id: number
  custos: Cost[]
  historico: unknown[]
}

export type DebtsResponse = {
  property_id: number
  dividas: Debt[]
  historico: unknown[]
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch {
    throw new PropertiesServiceError('Não foi possível conectar ao servidor. Tente novamente.')
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : 'Não foi possível concluir a operação.'
    throw new PropertiesServiceError(detail, response.status)
  }
  return payload as T
}

export async function listCosts(propertyId: number): Promise<Cost[]> {
  const payload = await request<CostsResponse>(`/api/imoveis/${propertyId}/custos`)
  return payload.custos
}

export function createCost(propertyId: number, payload: CostCreate): Promise<Cost> {
  return request<Cost>(`/api/imoveis/${propertyId}/custos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function listDebts(propertyId: number): Promise<Debt[]> {
  const payload = await request<DebtsResponse>(`/api/imoveis/${propertyId}/dividas`)
  return payload.dividas
}

export function createDebt(propertyId: number, payload: DebtCreate): Promise<Debt> {
  return request<Debt>(`/api/imoveis/${propertyId}/dividas`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function formatMoney(value?: number | string | null) {
  if (value === undefined || value === null || value === '') return 'Não informado'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(numeric)
}

export function formatPercent(value?: number | string | null) {
  if (value === undefined || value === null || value === '') return 'Não informado'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)
  return `${(numeric * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`
}

// Premissas financeiras (Task 3). Percentuais em fração (0.05 = 5%).
export type FinanceAssumptions = {
  goal_kind?: 'LUCRO_MINIMO' | 'MARGEM_MINIMA' | 'ROI_MINIMO' | null
  goal_value?: number | null
  corretagem_pct?: number | null
  tributo_pct?: number | null
  tax_base?: 'GANHO' | 'VENDA'
  valor_venda_estimado?: number | null
  prazo_meses?: number | null
  carregamento_mensal?: number | null
  cenarios?: unknown[]
}

export type FinanceResult = {
  custo_total?: number | string | null
  custo_saida?: number | string | null
  valor_mercado?: number | string | null
  resultado_liquido?: number | string | null
  resultado_provisorio?: boolean
  resultado_completo?: boolean
  margem_liquida?: number | string | null
  roi_operacao?: number | string | null
  preco_maximo?: number | string | null
  preco_maximo_definitivo?: boolean
  preco_maximo_provisorio?: boolean
  preco_maximo_detalhe?: { viavel?: boolean; definitivo?: boolean; provisorio?: boolean; razao?: string; mensagem?: string; pendencias?: string[]; custos_desconhecidos?: string[]; premissas_utilizadas?: Record<string, unknown> }
  cenarios?: Array<Record<string, unknown>>
  pendencias?: string[]
  custos_status?: Record<string, string>
  [key: string]: unknown
}

export type FinanceResponse = {
  property_id: number
  analysis_version?: number | null
  premissas?: FinanceAssumptions | null
  financeiro: FinanceResult
  historico?: unknown[]
}

export function getFinance(propertyId: number): Promise<FinanceResponse> {
  return request<FinanceResponse>(`/api/imoveis/${propertyId}/financeiro`)
}

export function saveFinanceAssumptions(propertyId: number, payload: FinanceAssumptions): Promise<FinanceResponse> {
  return request<FinanceResponse>(`/api/imoveis/${propertyId}/financeiro/premissas`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
