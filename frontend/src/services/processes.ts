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
  // Classificação do vínculo processo×imóvel (integração judicial).
  link_origin?: 'AUTOMATICA' | 'MANUAL' | 'VALIDADA' | 'NAO_CONFIRMADA' | null
  correlation_level?: 'ALTA' | 'MEDIA' | 'BAIXA' | 'NAO_CONFIRMADA' | null
  created_at?: string
}

// Critérios de pesquisa judicial. Só são enviados os que o usuário informar;
// nenhum CPF/CNPJ é presumido.
export type JudicialSearchCriteria = {
  process_number?: string
  cpf?: string
  cnpj?: string
  name?: string
  uf?: string
  tribunals?: string[]
  justice_types?: string[]
}

export type JudicialSource = {
  tribunal?: string | null
  status?: string | null
  [key: string]: unknown
}

export type JudicialSearchResult = {
  property_id: number
  disponivel: boolean
  status?: string
  mensagem?: string
  search_id?: string | null
  processos_criados?: number
  processos_atualizados?: number
  processos_relevantes?: number
  sinais_criados?: number
  fontes?: JudicialSource[]
  avisos?: string[]
}

export type JudicialLink = {
  link_origin: 'MANUAL' | 'VALIDADA' | 'NAO_CONFIRMADA'
  observacao?: string
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

// Pesquisa judicial pela Judicial API (DataJud) a partir do imóvel. Envia só os
// critérios preenchidos; a API responde com disponivel=false em degradação.
export function searchJudicial(propertyId: number, criteria: JudicialSearchCriteria): Promise<JudicialSearchResult> {
  const body: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(criteria)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value) && value.length === 0) continue
    body[key] = value
  }
  return request<JudicialSearchResult>(`/api/imoveis/${propertyId}/processos/consultar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// TASK 75.2: edição dos dados CADASTRAIS do processo (histórico before/after +
// evento). NÃO edita movimentações (append-only) nem a correlação determinística.
export type ProcessUpdate = Partial<Omit<ProcessCreate, 'evidence_id'>>

export function updateProcess(propertyId: number, processId: number, payload: ProcessUpdate): Promise<{ processo: LegalProcess }> {
  return request<{ processo: LegalProcess }>(`/api/imoveis/${propertyId}/processos/${processId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export type ProcessMovementCreate = { movement_date?: string; description: string; source?: string }

// Movimentação processual é APPEND-ONLY: cada andamento é um novo registro.
export function addProcessMovement(propertyId: number, processId: number, payload: ProcessMovementCreate): Promise<{ process_id: number; movimentacao: { id: number; description: string } }> {
  return request<{ process_id: number; movimentacao: { id: number; description: string } }>(`/api/imoveis/${propertyId}/processos/${processId}/movimentacoes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function linkJudicialProcess(propertyId: number, processId: number, payload: JudicialLink): Promise<{ property_id: number; processo: LegalProcess }> {
  return request<{ property_id: number; processo: LegalProcess }>(`/api/imoveis/${propertyId}/juridico/processos/${processId}/vincular`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
