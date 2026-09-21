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

export type RegistrationResponse = {
  property_id: number
  atual: PropertyRegistration | null
  historico: PropertyRegistration[]
  alteracoes: unknown[]
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
