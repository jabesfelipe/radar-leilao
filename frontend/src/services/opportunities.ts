// Serviço de Oportunidades + Workflow + Dashboard (Onda 2).
// Autenticação via wrapper global de fetch (Authorization injetado por session.ts).
import { PropertiesServiceError } from './properties'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(`${API_BASE_URL}${path}`, init) }
  catch { throw new PropertiesServiceError('Não foi possível conectar ao servidor. Tente novamente.') }
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : 'Não foi possível concluir a operação.'
    throw new PropertiesServiceError(detail, response.status)
  }
  return payload as T
}

const json = (method: string, body: unknown): RequestInit => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export type Modality = { code: string; name: string; description: string; track: string; status: string }
export type OpportunityRow = {
  id: number; property_id: number; codigo?: string | null; modality: string; status: string
  municipio?: string | null; current_phase: string; blocked: boolean
}
export type PhaseEvaluation = {
  phase: string; phase_state: string; gate_satisfied: boolean; active_hard_stops: string[]
  blocked: boolean; forward_targets: string[]; next_action: string; ruleset_version: string
}
export type TransitionDecision = {
  allowed: boolean; result: string; transition_type: string | null; from_phase: string
  to_phase: string; reason: string; active_hard_stops: string[]
}
export type HardStop = { code: string; description: string; blocks_phase: string; gravidade: string; acao_necessaria: string }
export type TransitionRow = {
  id: number; from_phase: string | null; to_phase: string; transition_type: string; result: string
  phase_state: string; hard_stops: string[]; decision?: string | null; justification?: string | null
  actor: string; created_at: string
}
export type DashboardData = {
  total_oportunidades: number; bloqueadas: number
  por_status: Record<string, number>; por_modalidade: Record<string, number>
  por_fase: Record<string, number>; por_municipio: Record<string, number>
  riscos_criticos_ativos: number
}

export const listModalities = () => request<{ ruleset_version: string; modalidades: Modality[] }>('/api/oportunidades/modalidades')

export const listOpportunities = (params: Record<string, string | number | undefined> = {}) => {
  const qs = Object.entries(params).filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&')
  return request<{ total: number; limit: number; offset: number; itens: OpportunityRow[] }>(`/api/oportunidades${qs ? `?${qs}` : ''}`)
}

export const createOpportunity = (data: { property_id: number; modality?: string; codigo?: string; origin?: string }) =>
  request<{ oportunidade: OpportunityRow; workflow: unknown }>('/api/oportunidades', json('POST', data))

export const getOpportunity = (id: number) =>
  request<{ oportunidade: OpportunityRow; imovel: unknown; workflow: Record<string, unknown>; fase: PhaseEvaluation }>(`/api/oportunidades/${id}`)

export const getTransitions = (id: number) => request<{ transicoes: TransitionDecision[] }>(`/api/oportunidades/${id}/transicoes`)
export const getHardStops = (id: number) => request<{ hard_stops: HardStop[] }>(`/api/oportunidades/${id}/hard-stops`)
export const getPending = (id: number) => request<Record<string, unknown>>(`/api/oportunidades/${id}/pendencias`)
export const getHistory = (id: number) => request<{ historico: TransitionRow[] }>(`/api/oportunidades/${id}/historico`)

export const setPhaseState = (id: number, data: { state: string; phase?: string; justification?: string }) =>
  request<Record<string, unknown>>(`/api/oportunidades/${id}/fase/estado`, json('POST', data))

export const requestTransition = (id: number, data: { target_phase: string; transition_type?: string; justification?: string; decision?: string }) =>
  request<{ decision: TransitionDecision; transition_id: number; workflow: Record<string, unknown> }>(`/api/oportunidades/${id}/transicao`, json('POST', data))

export const classifyModality = (id: number, data: { signals_text?: string; origin?: string; evidence_id?: number; confirm?: boolean }) =>
  request<Record<string, unknown>>(`/api/oportunidades/${id}/modalidade/classificar`, json('POST', data))

export const correctModality = (id: number, data: { modality: string; justification: string }) =>
  request<Record<string, unknown>>(`/api/oportunidades/${id}/modalidade/corrigir`, json('POST', data))

export const getDashboard = () => request<DashboardData>('/api/dashboard/oportunidades')

// Monitoramento de saúde do RAG (Fase 7): cobertura de embeddings e versões em erro.
export type RagHealth = {
  documentos: number
  versoes: number
  versoes_em_erro: number
  embeddings: {
    chunks_total: number
    chunks_com_embedding: number
    chunks_sem_embedding: number
    cobertura_pct: number
    versions_com_pendencia: number
    modelo: string
    dimensao: number
    provider_disponivel: boolean
  }
}

export const getRagHealth = () => request<RagHealth>('/api/monitoring/rag')
