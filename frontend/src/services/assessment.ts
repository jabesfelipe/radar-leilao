import { PropertiesServiceError } from './properties'

export type Risk = {
  id: number
  property_id?: number
  category?: string | null
  description?: string | null
  severity?: string | null
  impact?: string | null
  confidence?: string | null
  status?: string | null
  origin?: string | null
  evidence_id?: number | null
  analysis_version?: number | null
}

export type Verdict = {
  id: number
  property_id?: number
  analysis_version?: number | null
  overall?: string | null
  summary?: string | null
  what_is_known?: string | null
  what_is_unknown?: string | null
  pending_items?: string[] | null
  financial?: Record<string, unknown> | null
  risk_ids?: number[] | null
  evidence_ids?: number[] | null
}

/** Recomendação e fundamentos do veredito (motor determinístico; vem em `veredito.financial.decisao`). */
export type VerdictRecommendation = {
  codigo: 'NAO_ARREMATAR' | 'ARREMATAR_SOMENTE_APOS_RESOLVER_RISCOS' | 'ARREMATAR_ATE_PRECO_MAXIMO' | 'COMPLETAR_ANALISE' | string
  texto: string
  lance_maximo?: number | null
  lance_maximo_definitivo?: boolean
  lance_pretendido?: number | null
}

export type VerdictGround = {
  tipo: 'RISCO_JURIDICO' | 'RISCO_OPERACIONAL' | 'INVIABILIDADE_FINANCEIRA' | 'VIABILIDADE_FINANCEIRA' | 'PENDENCIA_DOCUMENTAL' | 'PENDENCIA_FINANCEIRA' | 'ANALISE_AUTOMATICA_INDISPONIVEL' | string
  descricao: string
  gravidade?: string | null
  categoria?: string | null
}

export type VerdictDecisionDetail = {
  recomendacao?: VerdictRecommendation | null
  fundamentos?: VerdictGround[] | null
  avaliacao_financeira?: { status?: 'VIAVEL' | 'INVIAVEL' | 'INDETERMINADO' | string; motivos?: string[]; faltantes?: string[] } | null
  analise_automatica_disponivel?: boolean | null
}

export function verdictDecision(verdict: Verdict | null | undefined): VerdictDecisionDetail | null {
  const decisao = (verdict?.financial as { decisao?: VerdictDecisionDetail } | null | undefined)?.decisao
  return decisao && typeof decisao === 'object' ? decisao : null
}

export type VerdictEvidence = {
  id: number
  documento?: string | null
  document_type?: string | null
  version?: number | null
  document_version_id?: number | null
  category?: string | null
  page?: number | null
  section?: string | null
  fact?: string | null
  source_excerpt?: string | null
  interpretation?: string | null
  hypothesis?: string | null
  confidence?: string | null
  chunk_id?: number | null
  tem_trecho_documento?: boolean
  // v1.0.4: de onde vem a informação e quanto o trecho citado a sustenta (ausentes em registros anteriores).
  origin?: 'DOCUMENTO' | 'CADASTRO' | 'CALCULO' | 'PESQUISA_JUDICIAL' | 'INFERENCIA_IA' | 'REGRA_DETERMINISTICA' | string | null
  strength?: 'FORTE' | 'MODERADA' | 'FRACA' | 'INVALIDA' | string | null
  agent?: string | null
}

// Confronto matrícula × edital (v1.0.4): determinístico, com as duas fontes e o trecho literal de cada uma.
export type ComparisonSide = {
  valor?: string | null
  valor_texto?: string | null
  documento?: string | null
  pagina?: number | null
  chunk_id?: number | null
  trecho?: string | null
}

export type DocumentComparison = {
  informacao: string
  matricula?: ComparisonSide | null
  edital?: ComparisonSide | null
  resultado: 'CONFERE' | 'DIVERGENCIA' | 'NAO_COMPARAVEL' | string
  observacao?: string | null
}

export type Assessment = {
  risks: Risk[]
  verdict: Verdict | null
  evidences: VerdictEvidence[]
  comparisons: DocumentComparison[]
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

export async function getAssessment(propertyId: number): Promise<Assessment> {
  const payload = await request<{ riscos?: Risk[]; veredito?: Verdict | null; veredito_evidencias?: VerdictEvidence[]; confronto_documental?: DocumentComparison[] }>(`/api/imoveis/${propertyId}`)
  return { risks: payload.riscos ?? [], verdict: payload.veredito ?? null, evidences: payload.veredito_evidencias ?? [], comparisons: payload.confronto_documental ?? [] }
}
