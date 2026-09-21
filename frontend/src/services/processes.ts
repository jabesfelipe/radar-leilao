import { PropertiesServiceError } from './properties'

export type LegalProcess = {
  id: number
  property_id: number
  number: string
  court?: string | null
  comarca?: string | null
  nature?: string | null
  subject?: string | null
  status?: string | null
  polo_active?: string | null
  polo_passive?: string | null
  distribution_date?: string | null
  observations?: string | null
  source?: string | null
  impact?: string | null
  evidence_id?: number | null
  created_at?: string
}

export type ProcessCreate = {
  number: string
  court?: string
  comarca?: string
  nature?: string
  subject?: string
  status?: string
  polo_active?: string
  polo_passive?: string
  distribution_date?: string
  observations?: string
  source?: string
  impact?: string
  evidence_id?: number
}

export type ProcessesResponse = {
  property_id: number
  processos: LegalProcess[]
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

export async function listProcesses(propertyId: number): Promise<LegalProcess[]> {
  const payload = await request<ProcessesResponse>(`/api/imoveis/${propertyId}/processos`)
  return payload.processos
}

export function createProcess(propertyId: number, payload: ProcessCreate): Promise<LegalProcess> {
  return request<LegalProcess>(`/api/imoveis/${propertyId}/processos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
