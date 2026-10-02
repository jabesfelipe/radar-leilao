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

// Edição de portal: todos os campos opcionais. `secret` só é enviado quando o
// operador deseja TROCAR a credencial (o backend cifra; nunca retorna o valor).
export type PortalAccessUpdate = Partial<PortalAccessCreate>

export const listAuctioneers = () => request<Auctioneer[]>('/api/leiloeiros')
export const getAuctioneer = (id: number) => request<Auctioneer>(`/api/leiloeiros/${id}`)

export const createAuctioneer = (payload: AuctioneerCreate) =>
  request<Auctioneer>('/api/leiloeiros', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const updateAuctioneer = (id: number, payload: Partial<AuctioneerCreate>) =>
  request<Auctioneer>(`/api/leiloeiros/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const addPortalAccess = (id: number, payload: PortalAccessCreate) =>
  request<PortalAccess>(`/api/leiloeiros/${id}/portais`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const updatePortalAccess = (auctioneerId: number, portalId: number, payload: PortalAccessUpdate) =>
  request<PortalAccess>(`/api/leiloeiros/${auctioneerId}/portais/${portalId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

// TASK 75.1: a credencial só é recuperada com o token de administração, enviado
// no header X-Portal-Admin-Token. Sem token, o backend recusa (401/503).
export const revealPortalSecret = (auctioneerId: number, portalId: number, adminToken: string) =>
  request<{ portal_id: number; username?: string | null; secret?: string | null }>(
    `/api/leiloeiros/${auctioneerId}/portais/${portalId}/credencial`,
    { headers: { 'X-Portal-Admin-Token': adminToken } },
  )

export const addAuctioneerDocument = (id: number, payload: { doc_type: string; name: string; file_path?: string; version?: number; observations?: string }) =>
  request<AuctioneerDocument>(`/api/leiloeiros/${id}/documentos`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

// GAP 3: associa um leiloeiro cadastrado ao leilão corrente do imóvel. O backend
// preserva o texto histórico (`auctioneer`) e grava a FK `auctioneer_id`.
export const linkAuctionAuctioneer = (propertyId: number, auctioneerId: number) =>
  request<{ property_id: number; auction_id: number; auctioneer_id: number; auctioneer_nome: string }>(
    `/api/imoveis/${propertyId}/leilao/leiloeiro`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ auctioneer_id: auctioneerId }) },
  )
