import { PropertiesServiceError } from './properties'

export type Risk = {
  id: number
  property_id?: number
  category?: string | null
  description?: string | null
  severity?: string | null
  impact?: string | null
  confidence?: string | null
  status?: string | null
  origin?: string | null
  evidence_id?: number | null
  analysis_version?: number | null
}

export type Verdict = {
  id: number
  property_id?: number
  analysis_version?: number | null
  overall?: string | null
  summary?: string | null
  what_is_known?: string | null
  what_is_unknown?: string | null
  pending_items?: string[] | null
  financial?: Record<string, unknown> | null
  risk_ids?: number[] | null
  evidence_ids?: number[] | null
}

export type Assessment = {
  risks: Risk[]
  verdict: Verdict | null
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

export async function getAssessment(propertyId: number): Promise<Assessment> {
  const payload = await request<{ riscos?: Risk[]; veredito?: Verdict | null }>(`/api/imoveis/${propertyId}`)
  return { risks: payload.riscos ?? [], verdict: payload.veredito ?? null }
}
