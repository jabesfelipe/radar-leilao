export type Property = {
  id: number
  title: string
  address: string
  city: string
  state: string
  property_type: string
  neighborhood?: string | null
  area_m2?: number | string
  private_area_m2?: number | string | null
  bedrooms?: number
  parking_spots?: number | null
  description?: string | null
  origin?: string | null
  origin_property_code?: string | null
  inscription?: string | null
  modality?: string | null
  system?: string | null
  status: string
  created_at?: string
}

export type PropertyCreate = {
  title: string
  address: string
  city: string
  state: string
  property_type: string
}

// Cadastro completo (wizard). Reutiliza o endpoint transacional POST /api/imoveis/completo.
export type PropertyBasics = {
  title: string
  address?: string
  city: string
  state: string
  property_type: string
  neighborhood?: string
  area_m2?: number
  private_area_m2?: number
  bedrooms?: number
  parking_spots?: number
  description?: string
  origin?: string
  origin_property_code?: string
  inscription?: string
  modality?: string
  system?: string
}

export type AuctionInput = {
  auction_stage?: string
  appraisal_value?: number
  bid_value?: number
  first_auction_date?: string
  first_auction_value?: number
  second_auction_date?: string
  second_auction_value?: number
  auctioneer?: string
  notice_url?: string
}

export type AuctionNoticeInput = {
  identifier?: string
  item?: string
  notice_date?: string
  auction_stage?: string
  appraisal_value?: number
  minimum_value?: number
  auction_date?: string
  auctioneer?: string
  observations?: string
}

export type RegistrationInput = {
  registration_number?: string
  registry_office?: string
  comarca?: string
  consultation_date?: string
  holder?: string
  observations?: string
}

export type SourceType = 'PAGINA_IMOVEL' | 'EDITAL' | 'MATRICULA' | 'OUTRA'

export type PropertySourceInput = {
  source_type: SourceType
  url?: string
  description?: string
  origin?: string
}

export type PropertyFullCreate = {
  imovel: PropertyBasics
  leilao?: AuctionInput
  edital?: AuctionNoticeInput
  matricula?: RegistrationInput
  fontes?: PropertySourceInput[]
}

export type PropertyFullResult = {
  id: number
  status: string
}

export type PropertySource = {
  id: number
  property_id: number
  source_type: SourceType
  url?: string | null
  description?: string | null
  origin?: string | null
  created_at?: string
}

export class PropertiesServiceError extends Error {
  status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'PropertiesServiceError'
    this.status = status
  }
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

export function listProperties(): Promise<Property[]> {
  return request<Property[]>('/api/imoveis')
}

export function createProperty(payload: PropertyCreate): Promise<Property> {
  return request<Property>('/api/imoveis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function createPropertyFull(payload: PropertyFullCreate): Promise<PropertyFullResult> {
  return request<PropertyFullResult>('/api/imoveis/completo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function listSources(id: number): Promise<PropertySource[]> {
  return request<PropertySource[]>(`/api/imoveis/${id}/fontes`)
}

export type AuctionSummary = {
  id: number
  auction_stage?: string | null
  appraisal_value?: number | string | null
  bid_value?: number | string | null
  first_auction_date?: string | null
  first_auction_value?: number | string | null
  second_auction_date?: string | null
  second_auction_value?: number | string | null
  auctioneer?: string | null
}

export type NoticeSummary = {
  id: number
  identifier?: string | null
  item?: string | null
}

export type RegistrationSummary = {
  id: number
  registration_number?: string | null
  registry_office?: string | null
  comarca?: string | null
}

export type PropertyDetail = {
  imovel: Property
  leilao: AuctionSummary | null
  edital: NoticeSummary | null
  matricula: RegistrationSummary | null
  fontes: PropertySource[]
}

export async function getProperty(id: number): Promise<Property> {
  const detail = await request<{ imovel: Property }>(`/api/imoveis/${id}`)
  return detail.imovel
}

export function getPropertyDetail(id: number): Promise<PropertyDetail> {
  return request<PropertyDetail>(`/api/imoveis/${id}`)
}

export type AnalysisResult = {
  versao: number
  agentes: string[]
  llm_usada: boolean
  modelo?: string | null
  chunks_recuperados: number[]
  evidencias: number[]
  veredito?: string | null
  status: string
}

export function analyzeProperty(id: number): Promise<AnalysisResult> {
  return request<AnalysisResult>(`/api/imoveis/${id}/analisar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
}
