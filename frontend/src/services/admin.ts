// Serviço do módulo administrativo (Etapa A — Central de Débitos/Parâmetros).
// Leituras são abertas; ESCRITAS exigem o header X-Admin-Token (proteção provisória
// até auth/RBAC — Onda 11). O token é fornecido pelo operador na própria tela e NÃO
// é persistido pelo frontend.

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class AdminServiceError extends Error {
  status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.name = 'AdminServiceError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch {
    throw new AdminServiceError('Não foi possível conectar ao servidor. Tente novamente.')
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : 'Não foi possível concluir a operação.'
    throw new AdminServiceError(detail, response.status)
  }
  return payload as T
}

function adminHeaders(token?: string): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['X-Admin-Token'] = token
  return headers
}

// --- Tipos ---
export type Municipality = {
  id: number; name: string; state: string; ibge_code?: string | null
  coverage_active: boolean; status: string; observations?: string | null
}
export type DebtType = {
  id: number; code: string; label: string; group: string; default_nature: string
  canonical_cost_key?: string | null; impacts_finance: boolean; active: boolean; description?: string | null
}
export type DebtSource = {
  id: number; municipality_id: number; debt_category?: string | null; name: string
  authority?: string | null; official_url?: string | null; source_type: string; method?: string | null
  situation: string; access_requirements?: string | null; limitations?: string | null
  observations?: string | null; last_validated_at?: string | null; active: boolean
}
export type Parameter = {
  id: number; key: string; name: string; description?: string | null; category: string
  data_type: string; scope: string; municipality_id?: number | null; debt_category?: string | null
  value?: string | null; default_value?: string | null; unit?: string | null
  min_value?: string | null; max_value?: string | null; status: string; version: number
  updated_by: string; created_at?: string; updated_at?: string
}
export type ParameterHistoryItem = {
  id: number; version: number; action: string; previous_value?: string | null
  new_value?: string | null; actor: string; justification?: string | null; created_at: string
}
export type Coverage = {
  id: number; municipality_id: number; debt_type_code: string; level: string
  situation: string; method: string; active: boolean; source_id?: number | null
  identifier_required?: string | null; limitations?: string | null
  observations?: string | null; last_validated_at?: string | null
}
export type CoverageGap = { municipality_id: number; debt_type_code: string; level: string }
export type CoverageMatrix = {
  total: number; itens: Coverage[]; nao_investigados: CoverageGap[]; ressalva: string
}

type ListResponse<T> = { total: number; itens: T[] }

// --- Municípios ---
export const listMunicipalities = () => request<ListResponse<Municipality>>('/api/admin/municipios')
export const createMunicipality = (data: Partial<Municipality>, token: string) =>
  request<Municipality>('/api/admin/municipios', { method: 'POST', headers: adminHeaders(token), body: JSON.stringify(data) })
export const updateMunicipality = (id: number, data: Partial<Municipality>, token: string) =>
  request<Municipality>(`/api/admin/municipios/${id}`, { method: 'PATCH', headers: adminHeaders(token), body: JSON.stringify(data) })

// --- Tipos de débito ---
export const listDebtTypes = () => request<ListResponse<DebtType>>('/api/admin/tipos-debito')
export const createDebtType = (data: Partial<DebtType>, token: string) =>
  request<DebtType>('/api/admin/tipos-debito', { method: 'POST', headers: adminHeaders(token), body: JSON.stringify(data) })

// --- Fontes ---
export const listSources = () => request<ListResponse<DebtSource>>('/api/admin/fontes')
export const createSource = (data: Partial<DebtSource>, token: string) =>
  request<DebtSource>('/api/admin/fontes', { method: 'POST', headers: adminHeaders(token), body: JSON.stringify(data) })
export const updateSource = (id: number, data: Partial<DebtSource>, token: string) =>
  request<DebtSource>(`/api/admin/fontes/${id}`, { method: 'PATCH', headers: adminHeaders(token), body: JSON.stringify(data) })

// --- Cobertura municipal × tipo (Etapa B) ---
export const listCoverage = (municipalityId?: number) =>
  request<CoverageMatrix>(`/api/admin/cobertura${municipalityId != null ? `?municipality_id=${municipalityId}` : ''}`)
export const createCoverage = (data: Partial<Coverage>, token: string) =>
  request<Coverage>('/api/admin/cobertura', { method: 'POST', headers: adminHeaders(token), body: JSON.stringify(data) })
export const updateCoverage = (id: number, data: Partial<Coverage> & { mark_validated?: boolean }, token: string) =>
  request<Coverage>(`/api/admin/cobertura/${id}`, { method: 'PATCH', headers: adminHeaders(token), body: JSON.stringify(data) })

// --- Parâmetros ---
export const listParameters = () => request<ListResponse<Parameter>>('/api/admin/parametros')
export const createParameter = (data: Partial<Parameter> & { justification?: string }, token: string) =>
  request<Parameter>('/api/admin/parametros', { method: 'POST', headers: adminHeaders(token), body: JSON.stringify(data) })
export const updateParameter = (id: number, data: Partial<Parameter> & { justification?: string }, token: string) =>
  request<Parameter>(`/api/admin/parametros/${id}`, { method: 'PATCH', headers: adminHeaders(token), body: JSON.stringify(data) })
export const parameterHistory = (id: number) =>
  request<{ parameter_id: number; historico: ParameterHistoryItem[] }>(`/api/admin/parametros/${id}/historico`)
