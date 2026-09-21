import { PropertiesServiceError } from './properties'

export const CHECKLIST_STATES = [
  'PENDENTE',
  'EM_ANALISE',
  'CONFIRMADO',
  'RISCO_IDENTIFICADO',
  'ATENCAO',
  'NAO_IDENTIFICADO',
  'NAO_APLICAVEL',
] as const

export type ChecklistState = (typeof CHECKLIST_STATES)[number]

export const CHECKLIST_CONFIDENCES = ['BAIXA', 'MEDIA', 'ALTA'] as const

export type ChecklistConfidence = (typeof CHECKLIST_CONFIDENCES)[number]

export type ChecklistItem = {
  id: number
  item_number?: number
  canonical_key?: string
  question: string
  description?: string | null
  category?: string | null
  domain?: string[] | null
  origin?: string | null
  active?: boolean
  applicable?: boolean
  required?: boolean
  item_version?: number
  state: string
  answer?: string | null
  confidence?: string | null
  interpretation?: string | null
  risk?: string | null
}

export type ChecklistUpdate = {
  state: ChecklistState
  answer?: string
  confidence?: ChecklistConfidence
  interpretation?: string | null
  risk?: string | null
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

export async function listChecklist(propertyId: number): Promise<ChecklistItem[]> {
  const payload = await request<{ checklist: ChecklistItem[] }>(`/api/imoveis/${propertyId}`)
  return payload.checklist ?? []
}

export function updateChecklistItem(propertyId: number, itemId: number, payload: ChecklistUpdate): Promise<ChecklistItem> {
  return request<ChecklistItem>(`/api/imoveis/${propertyId}/checklist/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
