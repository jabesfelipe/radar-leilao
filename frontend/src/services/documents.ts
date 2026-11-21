import { PropertiesServiceError } from './properties'

export type ProcessingStage = {
  etapa: 'upload' | 'ocr' | 'extracao' | 'chunking' | 'embedding' | 'indexacao' | string
  estado: 'concluida' | 'parcial' | 'pendente' | 'falhou' | 'indisponivel' | 'nao_aplicavel' | string
  detalhe: string
}

/** Prontidão derivada no backend (documents/readiness.py): etapas explícitas e se o documento pode ser analisado. */
export type VersionProcessing = {
  estado: string
  mensagem: string
  pronto_para_analise: boolean
  nivel_indexacao: 'vetorial' | 'parcial' | 'texto' | 'nenhum' | string
  chunks: number
  chunks_com_embedding: number
  etapas: ProcessingStage[]
}

export type DocumentVersion = {
  id: number
  version: number
  content_hash: string
  status: string
  processamento?: VersionProcessing | null
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
  return (await listDocumentsWithStatus(propertyId)).documents
}

/** v1.0.14: situação documental (recebidos, analisados, obrigatórios, incompletos, evidências e próximas ações). */
export type DocumentSituation = {
  texto: string
  contagem: { recebidos: number; analisados: number; incompletos: number; em_processamento: number; evidencias: number }
  obrigatorios_faltando: string[]
  esperados: { chave: string; nome: string; obrigatorio: boolean; situacao: string; por_que: string; proxima_acao: string | null }[]
  documentos: { id: number; nome: string; situacao: string; situacao_label: string; paginas?: number | null; paginas_citadas: number[]; evidencias: number;
    confianca: { alta: number; media: number; baixa: number }; pendencias: string[] }[]
  proximas_acoes: string[]
}

export async function listDocumentsWithStatus(propertyId: number): Promise<{ documents: PropertyDocument[]; situation: DocumentSituation | null }> {
  const payload = await request<{ documentos: PropertyDocument[]; situacao_documental?: DocumentSituation }>(`/api/imoveis/${propertyId}/documentos`)
  return { documents: payload.documentos, situation: payload.situacao_documental ?? null }
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
