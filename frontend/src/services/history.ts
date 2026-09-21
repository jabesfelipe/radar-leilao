import { PropertiesServiceError } from './properties'

export type DomainEvent = {
  id: number
  property_id?: number | null
  event_type: string
  aggregate_type?: string | null
  aggregate_id?: number | null
  affected_domains?: string[] | null
  processed?: boolean
  created_at?: string
}

export type AnalysisRecord = {
  id: number
  property_id?: number
  version: number
  scope?: string | null
  affected_domains?: string[] | null
  agents_executed?: string[] | null
  documents_considered?: number[] | null
  evidence_ids?: number[] | null
  changes?: string | null
  model?: string | null
  prompt_version?: string | null
  created_at?: string
}

export type PropertyHistory = {
  events: DomainEvent[]
  analyses: AnalysisRecord[]
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

export async function getHistory(propertyId: number): Promise<PropertyHistory> {
  const payload = await request<{ eventos?: DomainEvent[]; analises?: AnalysisRecord[] }>(`/api/imoveis/${propertyId}`)
  return { events: payload.eventos ?? [], analyses: payload.analises ?? [] }
}
