import { PropertiesServiceError } from './properties'

export type DocumentVersion = {
  id: number
  version: number
  content_hash: string
  original_path?: string | null
  normalized_path?: string | null
  status: string
  created_at?: string
}

export type PropertyDocument = {
  id: number
  property_id: number
  name: string
  document_type: string
  source: string
  status: string
  created_at?: string
  versions: DocumentVersion[]
}

export type DocumentUpload = {
  file: File
  document_type?: string
  source?: string
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

function buildForm({ file, document_type, source }: DocumentUpload) {
  const form = new FormData()
  form.append('file', file)
  if (document_type && document_type.trim()) form.append('document_type', document_type.trim())
  if (source && source.trim()) form.append('source', source.trim())
  return form
}

export async function listDocuments(propertyId: number): Promise<PropertyDocument[]> {
  const payload = await request<{ documentos: PropertyDocument[] }>(`/api/imoveis/${propertyId}/documentos`)
  return payload.documentos
}

export function uploadDocument(propertyId: number, upload: DocumentUpload): Promise<PropertyDocument> {
  return request<PropertyDocument>(`/api/imoveis/${propertyId}/documentos`, {
    method: 'POST',
    body: buildForm(upload),
  })
}

export function uploadDocumentVersion(documentId: number, upload: DocumentUpload): Promise<PropertyDocument> {
  return request<PropertyDocument>(`/api/documentos/${documentId}/versoes`, {
    method: 'POST',
    body: buildForm(upload),
  })
}

export function latestVersion(document: PropertyDocument): DocumentVersion | null {
  if (document.versions.length === 0) return null
  return document.versions.reduce((latest, current) => (current.version > latest.version ? current : latest))
}
