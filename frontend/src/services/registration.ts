import { PropertiesServiceError } from './properties'

export type PropertyRegistration = {
  id: number
  property_id: number
  registration_number?: string | null
  registry_office?: string | null
  comarca?: string | null
  consultation_date?: string | null
  holder?: string | null
  observations?: string | null
  document_version_id?: number | null
  evidence_id?: number | null
  created_at?: string
}

export type RegistrationCreate = {
  registration_number: string
  registry_office?: string
  comarca?: string
  consultation_date?: string
  holder?: string
  observations?: string
}

// Auditoria v6: titular atual pela sequência de atos da matrícula x titular gravado no cadastro.
export type HolderSummary = {
  titular_atual: string | null; ato: string | null; situacao: 'DETERMINADA' | 'INCONCLUSIVO'
  titular_cadastro: string | null; divergencia_cadastro: boolean; texto: string
}

export type RegistrationResponse = {
  property_id: number
  atual: PropertyRegistration | null
  historico: PropertyRegistration[]
  alteracoes: unknown[]
  titularidade?: HolderSummary
}

export type AuctionNotice = {
  id: number
  property_id: number
  identifier?: string | null
  notice_date?: string | null
  auction_stage?: string | null
  appraisal_value?: number | string | null
  minimum_value?: number | string | null
  auction_date?: string | null
  auctioneer?: string | null
  observations?: string | null
  document_version_id?: number | null
  evidence_id?: number | null
  created_at?: string
}

export type AuctionNoticeCreate = {
  identifier: string
  notice_date?: string
  auction_stage?: string
  appraisal_value?: number
  minimum_value?: number
  auction_date?: string
  auctioneer?: string
  observations?: string
}

export type AuctionNoticeResponse = {
  property_id: number
  atual: AuctionNotice | null
  historico: AuctionNotice[]
  alteracoes: unknown[]
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

export function getRegistration(propertyId: number): Promise<RegistrationResponse> {
  return request<RegistrationResponse>(`/api/imoveis/${propertyId}/matricula`)
}

export function createRegistration(propertyId: number, payload: RegistrationCreate): Promise<PropertyRegistration> {
  return request<PropertyRegistration>(`/api/imoveis/${propertyId}/matricula`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

// TASK 75.2: edição dos metadados da matrícula (histórico before/after). O
// documento anexo não é sobrescrito (versionamento documental à parte).
export type RegistrationUpdate = Partial<RegistrationCreate>

export function updateRegistration(propertyId: number, registrationId: number, payload: RegistrationUpdate): Promise<{ matricula: PropertyRegistration }> {
  return request<{ matricula: PropertyRegistration }>(`/api/imoveis/${propertyId}/matricula/${registrationId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

// v1.0.12: linha do tempo da matrícula, calculada dos trechos já armazenados (sem reprocessar).
export type TimelineParty = { papel: string; papel_descricao: string; nome: string; tipo_pessoa: 'FISICA' | 'JURIDICA'; como_identificado: string }
export type TimelineEvent = {
  ato: string; numero: number | null; tipo: string; tipo_descricao: string; data: string | null; data_texto: string | null
  partes: TimelineParty[]; valor: { valor: number | string; texto: string; rotulo: string } | null; construtora: string | null
  conclusao_obra: boolean; trecho: string; chunk_id: number | null; pagina: number | null; secao: string | null
  documento: { document_id: number | null; document_version_id: number | null; nome: string } | null; fonte: string
}
export type RegistryTimeline = {
  property_id: number; disponivel: boolean; motivo?: string; eventos: TimelineEvent[]
  idade: { anos: number | null; estimada: boolean; base: string | null; texto: string }
  datas_chave: { aquisicao?: { data: string; ato: string } | null; consolidacao?: { data: string; ato: string } | null }
  aviso_nomes?: string; atos_lidos: string[]
  titularidade?: Titularity
}

export type TitularityRow = {
  nome: string; tipo_pessoa: 'FISICA' | 'JURIDICA' | null; papel: string; ato: string | null; data: string | null; fonte: string | null
  trecho: string | null; status: 'ATUAL' | 'HISTORICO'; confianca: string; como_identificado: string | null; observacao: string | null
}
export type Titularity = {
  situacao: string; titular_atual: string | null; ato: string | null; trecho: string | null; confianca: string; texto: string
  partes: TitularityRow[]; aviso: string | null
}

export function getRegistryTimeline(propertyId: number): Promise<RegistryTimeline> {
  return request<RegistryTimeline>(`/api/imoveis/${propertyId}/matricula/linha-do-tempo`)
}

export function getNotice(propertyId: number): Promise<AuctionNoticeResponse> {
  return request<AuctionNoticeResponse>(`/api/imoveis/${propertyId}/edital`)
}

export function createNotice(propertyId: number, payload: AuctionNoticeCreate): Promise<AuctionNotice> {
  return request<AuctionNotice>(`/api/imoveis/${propertyId}/edital`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

// TASK 75.2: edição dos metadados do edital (histórico before/after). Documento
// original preservado (versionamento documental à parte).
export type AuctionNoticeUpdate = Partial<AuctionNoticeCreate>

export function updateNotice(propertyId: number, noticeId: number, payload: AuctionNoticeUpdate): Promise<{ edital: AuctionNotice }> {
  return request<{ edital: AuctionNotice }>(`/api/imoveis/${propertyId}/edital/${noticeId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
