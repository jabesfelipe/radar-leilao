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
  /** v1.0.11: resultado para o investidor, derivado no backend (fonte única da classificação). */
  resultado?: ChecklistOutcome | null
  resultado_label?: string | null
  acao_recomendada?: string | null
  fonte_necessaria?: string | null
  evidence_ids?: number[]
  resolution_origin?: string | null
  /** v1.0.14: prioridade P0 (bloqueador) a P3 (complementar), explicação, próxima ação e responsável. */
  prioridade?: 'P0' | 'P1' | 'P2' | 'P3' | string | null
  prioridade_label?: string | null
  explicacao?: string | null
  proxima_acao?: string | null
  responsavel?: string | null
}

export type ChecklistOutcome = 'CONFIRMADO' | 'RISCO_IDENTIFICADO' | 'PENDENTE' | 'INCONCLUSIVO' | 'NAO_APLICAVEL' | 'SEM_RESTRICAO_IDENTIFICADA'

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
  question?: string | null
  resultado?: ChecklistOutcome | null
  resultado_label?: string | null
  acao_recomendada?: string | null
  fonte_necessaria?: string | null
  evidence_ids?: number[]
  resolution_origin?: string | null
  prioridade?: string | null
  prioridade_label?: string | null
  explicacao?: string | null
  proxima_acao?: string | null
  responsavel?: string | null
}

export type ChecklistEvidence = {
  id: number
  category?: string
  documento?: string
  document_type?: string
  version?: number
  page?: number
  section?: string
  fact?: string
  source_excerpt?: string
  confidence?: string
  origin?: string
  strength?: string
  agent?: string
  tipo_evidencia?: string
  tipo_evidencia_label?: string
  created_at?: string
  tem_trecho_documento?: boolean
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
      // pergunta adequada à modalidade (backend) > pergunta do catálogo > chave
      question: result.question ?? meta?.question ?? result.canonical_key ?? 'Item do checklist',
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
      resultado: result.resultado ?? null,
      resultado_label: result.resultado_label ?? null,
      acao_recomendada: result.acao_recomendada ?? null,
      fonte_necessaria: result.fonte_necessaria ?? null,
      evidence_ids: result.evidence_ids ?? [],
      resolution_origin: result.resolution_origin ?? null,
      prioridade: result.prioridade ?? null,
      prioridade_label: result.prioridade_label ?? null,
      explicacao: result.explicacao ?? null,
      proxima_acao: result.proxima_acao ?? null,
      responsavel: result.responsavel ?? null,
    }
  })
}

const PRIORITY_ORDER: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 }
const OPEN_OUTCOMES = new Set(['PENDENTE', 'INCONCLUSIVO', 'RISCO_IDENTIFICADO'])

/** v1.0.14: itens em aberto primeiro, depois por prioridade (P0 a P3); sem prioridade, mantém a ordem original. */
export function sortByPriority(items: ChecklistItem[]): ChecklistItem[] {
  if (!items.some((i) => i.prioridade)) return items
  return items
    .map((item, index) => ({ item, index }))
    .sort((a, b) => {
      const openA = OPEN_OUTCOMES.has(String(a.item.resultado ?? a.item.state)) ? 0 : 1
      const openB = OPEN_OUTCOMES.has(String(b.item.resultado ?? b.item.state)) ? 0 : 1
      if (openA !== openB) return openA - openB
      const pa = PRIORITY_ORDER[String(a.item.prioridade)] ?? 4
      const pb = PRIORITY_ORDER[String(b.item.prioridade)] ?? 4
      return pa !== pb ? pa - pb : a.index - b.index
    })
    .map((x) => x.item)
}

export function isOpenItem(item: ChecklistItem): boolean {
  return OPEN_OUTCOMES.has(String(item.resultado ?? item.state))
}

export async function listChecklistEvidence(propertyId: number, resultId: number): Promise<ChecklistEvidence[]> {
  const payload = await request<{ evidencias: ChecklistEvidence[] }>(`/api/imoveis/${propertyId}/checklist/${resultId}/evidencias`)
  return payload.evidencias ?? []
}

export function updateChecklistItem(propertyId: number, itemId: number, payload: ChecklistUpdate): Promise<ChecklistItem> {
  return request<ChecklistItem>(`/api/imoveis/${propertyId}/checklist/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
