import { PropertiesServiceError } from './properties'

export type MarketComparable = {
  id: number
  property_id?: number
  kind: string
  price?: number | string
  rent?: number | string | null
  area_m2?: number | string
  source?: string
  url?: string
  created_at?: string
}

export type ComparableCreate = {
  kind: string
  price?: number
  rent?: number
  area_m2?: number
  source?: string
  url?: string
}

export type OccupancyStatus = 'OCUPADO' | 'DESOCUPADO' | 'DESCONHECIDO'

export type Occupancy = {
  id: number
  property_id: number
  status: OccupancyStatus
  occupant_profile?: string | null
  estimated_cost?: number | string | null
  estimated_months?: number | null
  evidence_id?: number | null
  created_at?: string
  updated_at?: string
}

export type OccupancyCreate = {
  status: OccupancyStatus
  occupant_profile?: string
  estimated_cost?: number
  estimated_months?: number
  evidence_id?: number
}

export type OccupancyResponse = {
  property_id: number
  situacao_atual: Occupancy | null
  ultimo_registro: Occupancy | null
  historico: Occupancy[]
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

export async function listComparables(propertyId: number): Promise<MarketComparable[]> {
  const payload = await request<{ comparaveis: MarketComparable[] }>(`/api/imoveis/${propertyId}`)
  return payload.comparaveis ?? []
}

export function createComparable(propertyId: number, payload: ComparableCreate): Promise<MarketComparable> {
  return request<MarketComparable>(`/api/imoveis/${propertyId}/comparaveis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function getOccupancy(propertyId: number): Promise<OccupancyResponse> {
  return request<OccupancyResponse>(`/api/imoveis/${propertyId}/ocupacao`)
}

export function createOccupancy(propertyId: number, payload: OccupancyCreate): Promise<Occupancy> {
  return request<Occupancy>(`/api/imoveis/${propertyId}/ocupacao`, {
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
