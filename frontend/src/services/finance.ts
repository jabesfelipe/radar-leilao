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
