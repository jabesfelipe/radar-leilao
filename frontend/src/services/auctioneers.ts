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

// NOTA DE SEGURANÇA: o tipo PortalAccess NÃO possui `secret`. A senha nunca vem
// em listagens; só é obtida via revealPortalSecret (endpoint dedicado).
export type PortalAccess = {
  id: number
  auctioneer_id: number
  portal: string
  url?: string | null
  username?: string | null
  access_type?: string | null
  two_factor_enabled: boolean
  observations?: string | null
  status: string
  last_validated_at?: string | null
  has_secret: boolean
}

export type AuctioneerDocument = {
  id: number
  auctioneer_id: number
  doc_type: string
  name: string
  file_path?: string | null
  version: number
  observations?: string | null
}

export type Auctioneer = {
  id: number
  name: string
  document?: string | null
  company?: string | null
  registration?: string | null
  phone?: string | null
  email?: string | null
  website?: string | null
  address?: string | null
  observations?: string | null
  status: string
  portais?: PortalAccess[]
  documentos?: AuctioneerDocument[]
}

export type AuctioneerCreate = {
  name: string
  document?: string
  company?: string
  registration?: string
  phone?: string
  email?: string
  website?: string
  address?: string
  observations?: string
  status?: string
}

export type PortalAccessCreate = {
  portal: string
  url?: string
  username?: string
  secret?: string
  access_type?: string
  two_factor_enabled?: boolean
  observations?: string
  status?: string
}

export const listAuctioneers = () => request<Auctioneer[]>('/api/leiloeiros')
export const getAuctioneer = (id: number) => request<Auctioneer>(`/api/leiloeiros/${id}`)

export const createAuctioneer = (payload: AuctioneerCreate) =>
  request<Auctioneer>('/api/leiloeiros', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const updateAuctioneer = (id: number, payload: Partial<AuctioneerCreate>) =>
  request<Auctioneer>(`/api/leiloeiros/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const addPortalAccess = (id: number, payload: PortalAccessCreate) =>
  request<PortalAccess>(`/api/leiloeiros/${id}/portais`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const revealPortalSecret = (auctioneerId: number, portalId: number) =>
  request<{ portal_id: number; username?: string | null; secret?: string | null }>(`/api/leiloeiros/${auctioneerId}/portais/${portalId}/credencial`)

export const addAuctioneerDocument = (id: number, payload: { doc_type: string; name: string; file_path?: string; version?: number; observations?: string }) =>
  request<AuctioneerDocument>(`/api/leiloeiros/${id}/documentos`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
