// Serviço da Central de Débitos por imóvel (Etapas A–F).
// Leitura da consolidação por natureza, histórico de consultas e estimativa
// condominial. Determinístico; nenhuma consulta externa é feita pelo frontend.
import { PropertiesServiceError } from './properties'

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

function jsonInit(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

const base = (propertyId: number) => `/api/imoveis/${propertyId}`

export type Consolidation = {
  property_id: number
  totais: Record<string, number | string>
  contagens: Record<string, number>
  exposicao_passivo_com_ressalva: number | string
  ressalvas: string[]
}

export type DebtsView = {
  property_id: number
  debitos: Array<Record<string, unknown>>
  legado_debts: Array<Record<string, unknown>>
  consolidacao: Consolidation
}

export type DebtQueryRow = {
  id: number; debt_type_code: string; municipality_id?: number | null
  provider: string; mode: string; status: string; attempts: number
  duration_ms?: number | null; message?: string | null; debt_id?: number | null
  requested_at?: string | null; completed_at?: string | null
}

export type CondominiumEstimate = {
  possivel: boolean
  motivo?: string
  cenarios?: { conservador: number | string; provavel: number | string; otimista: number | string } | null
  confianca: string
  memoria_calculo: Record<string, unknown>
  parametros_usados: Array<Record<string, unknown>>
  status?: string
  natureza?: string
  ressalva?: string
}

export type AgeAlerts = {
  nivel: string | null
  conclusivo: boolean
  mensagem: string
  limites: { nivel_1_anos: number; nivel_2_anos: number }
}

export function getDebts(propertyId: number): Promise<DebtsView> {
  return request<DebtsView>(`${base(propertyId)}/debitos`)
}

export function getConsolidation(propertyId: number): Promise<Consolidation> {
  return request<Consolidation>(`${base(propertyId)}/debitos/consolidacao`)
}

export function listDebtQueries(propertyId: number): Promise<{ property_id: number; consultas: DebtQueryRow[] }> {
  return request(`${base(propertyId)}/debitos/consultas`)
}

export function runDebtQuery(propertyId: number, payload: Record<string, unknown>): Promise<unknown> {
  return request(`${base(propertyId)}/debitos/consultar`, jsonInit('POST', payload))
}

export function estimateCondominium(
  propertyId: number,
  payload: Record<string, unknown>,
): Promise<{ property_id: number; estimativa: CondominiumEstimate; alertas_idade: AgeAlerts; estimativa_id: number | null }> {
  return request(`${base(propertyId)}/debitos/estimar-condominio`, jsonInit('POST', payload))
}
