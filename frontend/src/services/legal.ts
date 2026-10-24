import { PropertiesServiceError } from './properties'

// ---- Tipos (espelham a serialização da Central Jurídica no backend) ----

export type LegalProvision = {
  id: number
  slug: string
  referencia: string
  titulo?: string | null
  texto_oficial?: string | null
  orientacao_pratica?: string | null
  contextos: string[]
  tags: string[]
  verificacao: string
  similaridade?: number
  fonte?: {
    slug: string
    rotulo: string
    tipo: string
    url_oficial?: string | null
    vigente: boolean
  }
}

export type LegalChecklistLink = {
  canonical_key: string
  relevancia: string
  nota?: string | null
  pergunta?: string | null
  categoria?: string | null
}

export type LegalRule = {
  id: number
  slug: string
  tipo: string
  titulo: string
  enunciado: string
  contextos: string[]
  severidade?: string | null
  base_legal?: LegalProvision | null
  itens_checklist?: LegalChecklistLink[]
  relevancia?: string
  nota?: string | null
}

export type LegalSource = {
  id: number
  slug: string
  tipo: string
  rotulo: string
  titulo: string
  orgao?: string | null
  url_oficial?: string | null
  ano?: number | null
  vigente: boolean
  verificacao: string
  resumo?: string | null
  dispositivos: LegalProvision[]
}

export type LibraryOverview = {
  total_fontes: number
  total_dispositivos: number
  total_regras: number
  itens_checklist_cobertos: number
  itens_checklist_total: number
  cobertura_checklist: Record<string, number>
  fontes: LegalSource[]
  regras: LegalRule[]
}

export type LibrarySearch = {
  query: string
  contexto?: string | null
  modo_busca: string
  total: number
  resultados: LegalProvision[]
}

export type ChecklistReferences = {
  canonical_key: string
  pergunta?: string | null
  categoria?: string | null
  existe_no_checklist: boolean
  total: number
  referencias: LegalRule[]
}

export type ContextReferences = {
  contexto: string
  total: number
  referencias: LegalRule[]
}

export type PropertyLegalCentral = {
  property_id: number
  sintese_juridica: {
    processos_encontrados: number
    processos_relevantes: number
    pendencias: string[]
    confirmados: string[]
    correlacao: string
    situacao_imovel: string
    risco_principal?: { descricao: string; severidade?: string | null; confianca?: string | null } | null
    impacto_financeiro: string
    diligencia_recomendada?: string | null
  }
  itens_com_base_legal: Array<{
    canonical_key: string
    pergunta: string
    estado: string
    categoria?: string | null
    referencias: LegalRule[]
  }>
  total_itens_com_base_legal: number
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

export function getLibrary(): Promise<LibraryOverview> {
  return request<LibraryOverview>('/api/juridico/biblioteca')
}

export function searchLibrary(query: string, context?: string): Promise<LibrarySearch> {
  const params = new URLSearchParams({ q: query })
  if (context) params.set('contexto', context)
  return request<LibrarySearch>(`/api/juridico/biblioteca/busca?${params.toString()}`)
}

export function getChecklistReferences(canonicalKey: string): Promise<ChecklistReferences> {
  return request<ChecklistReferences>(`/api/juridico/referencias/checklist/${encodeURIComponent(canonicalKey)}`)
}

export function getContextReferences(context: string): Promise<ContextReferences> {
  return request<ContextReferences>(`/api/juridico/referencias/contexto/${encodeURIComponent(context)}`)
}

export function getPropertyLegalCentral(propertyId: number): Promise<PropertyLegalCentral> {
  return request<PropertyLegalCentral>(`/api/imoveis/${propertyId}/juridico/central`)
}
