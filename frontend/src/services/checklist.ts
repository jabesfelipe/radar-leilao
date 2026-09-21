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
  applicable?: boolean | null
  required?: boolean
  item_version?: number
  state: string
  answer?: string | null
  confidence?: string | null
  interpretation?: string | null
  risk?: string | null
}

type ChecklistResult = {
  id: number
  checklist_item_id?: number
  canonical_key?: string
  item_version?: number
  applicable?: boolean | null
  state: string
  answer?: string | null
  confidence?: string | null
  interpretation?: string | null
  risk?: string | null
  previous_result_id?: number | null
}

type ChecklistExecution = {
  id: number
  created_at?: string
  results: ChecklistResult[]
}

type ChecklistMasterItem = {
  canonical_key: string
  question?: string
  description?: string | null
  category?: string | null
  domain?: string[] | null
  origin?: string | null
  priority?: number
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
  const executions = await request<ChecklistExecution[]>(`/api/imoveis/${propertyId}/checklist`)
  const latest = executions.length > 0 ? executions[executions.length - 1] : null
  const results = latest?.results ?? []
  if (results.length === 0) return []

  const master = await request<ChecklistMasterItem[]>(`/api/checklist`).catch(() => [] as ChecklistMasterItem[])
  const masterByKey = new Map(master.map((entry) => [entry.canonical_key, entry]))

  return results.map((result) => {
    const meta = result.canonical_key ? masterByKey.get(result.canonical_key) : undefined
    return {
      id: result.id,
      item_number: meta?.priority,
      canonical_key: result.canonical_key,
      question: meta?.question ?? result.canonical_key ?? 'Item do checklist',
      description: meta?.description ?? null,
      category: meta?.category ?? null,
      domain: meta?.domain ?? null,
      origin: meta?.origin ?? null,
      item_version: result.item_version,
      applicable: result.applicable ?? null,
      state: result.state,
      answer: result.answer ?? null,
      confidence: result.confidence ?? null,
      interpretation: result.interpretation ?? null,
      risk: result.risk ?? null,
    }
  })
}

export function updateChecklistItem(propertyId: number, itemId: number, payload: ChecklistUpdate): Promise<ChecklistItem> {
  return request<ChecklistItem>(`/api/imoveis/${propertyId}/checklist/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
