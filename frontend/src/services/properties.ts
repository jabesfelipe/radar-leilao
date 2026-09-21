export type Property = {
  id: number
  title: string
  address: string
  city: string
  state: string
  property_type: string
  area_m2?: number | string
  bedrooms?: number
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

export async function getProperty(id: number): Promise<Property> {
  const detail = await request<{ imovel: Property }>(`/api/imoveis/${id}`)
  return detail.imovel
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
