import { PropertiesServiceError } from './properties'

export type FrontSummary = {
  frente: string
  status: string
  integracao?: string | null
  ultima_consulta?: string | null
  pendencias?: string[]
  achados?: number
  revisado?: boolean
  // campos específicos por frente (opcionais)
  titular?: string | null
  matricula?: string | null
  processos?: number
  relevantes?: number
  homonimos?: number
  debitos_municipais?: number
  total_em_aberto?: number | string | null
  geocodificado?: boolean
  coordenadas_confirmadas?: boolean
}

export type LocationChecklistItem = { key: string; label: string; rating: string }

export type LocationView = {
  property_id: number
  endereco: string
  normalized_address?: string | null
  latitude?: number | null
  longitude?: number | null
  geocode_precision?: string | null
  geocode_source?: string | null
  geocoded_at?: string | null
  coordinates_confirmed: boolean
  maps_url?: string | null
  street_view_url?: string | null
  location_checklist: LocationChecklistItem[]
  observations?: string | null
  inspected_at?: string | null
  integracao_maps: string
}

export type DueDiligenceOverview = {
  property_id: number
  frentes: {
    MATRICULA: FrontSummary
    JUDICIAL: FrontSummary
    PREFEITURA: FrontSummary
    LOCALIZACAO: FrontSummary
  }
  localizacao: LocationView
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

function jsonInit(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

const base = (propertyId: number) => `/api/imoveis/${propertyId}`

export function getDueDiligence(propertyId: number): Promise<DueDiligenceOverview> {
  return request<DueDiligenceOverview>(`${base(propertyId)}/due-diligence`)
}

export function getLocation(propertyId: number): Promise<LocationView> {
  return request<LocationView>(`${base(propertyId)}/localizacao`)
}

export function updateLocation(propertyId: number, payload: Record<string, unknown>): Promise<LocationView> {
  return request<LocationView>(`${base(propertyId)}/localizacao`, jsonInit('PUT', payload))
}

export function geocodeLocation(propertyId: number, address?: string): Promise<{ integracao: string; localizacao: LocationView; mensagem?: string }> {
  return request(`${base(propertyId)}/localizacao/geocodificar`, jsonInit('POST', address ? { address } : {}))
}

export function addPrefeituraDebt(propertyId: number, payload: Record<string, unknown>): Promise<unknown> {
  return request(`${base(propertyId)}/due-diligence/prefeitura/debito`, jsonInit('POST', payload))
}

export function reviewFront(propertyId: number, frente: string, payload: Record<string, unknown>): Promise<FrontSummary> {
  return request<FrontSummary>(`${base(propertyId)}/due-diligence/${frente}/revisar`, jsonInit('POST', payload))
}
