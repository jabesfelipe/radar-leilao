// Serviço da Central de Débitos por imóvel (Etapas A–F).
// Leitura da consolidação por natureza, histórico de consultas e estimativa
// condominial. Determinístico; nenhuma consulta externa é feita pelo frontend.
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

function jsonInit(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

const base = (propertyId: number) => `/api/imoveis/${propertyId}`

export type Consolidation = {
  property_id: number
  totais: Record<string, number | string>
  contagens: Record<string, number>
  exposicao_passivo_com_ressalva: number | string
  ressalvas: string[]
}

export type DebtsView = {
  property_id: number
  debitos: Array<Record<string, unknown>>
  legado_debts: Array<Record<string, unknown>>
  consolidacao: Consolidation
}

export type DebtQueryRow = {
  id: number; debt_type_code: string; municipality_id?: number | null
  provider: string; mode: string; status: string; attempts: number
  duration_ms?: number | null; message?: string | null; debt_id?: number | null
  requested_at?: string | null; completed_at?: string | null
}

export type CondominiumEstimate = {
  possivel: boolean
  motivo?: string
  cenarios?: { conservador: number | string; provavel: number | string; otimista: number | string } | null
  confianca: string
  memoria_calculo: Record<string, unknown>
  parametros_usados: Array<Record<string, unknown>>
  status?: string
  natureza?: string
  ressalva?: string
}

export type AgeAlerts = {
  nivel: string | null
  conclusivo: boolean
  mensagem: string
  limites: { nivel_1_anos: number; nivel_2_anos: number }
}

export function getDebts(propertyId: number): Promise<DebtsView> {
  return request<DebtsView>(`${base(propertyId)}/debitos`)
}

export function getConsolidation(propertyId: number): Promise<Consolidation> {
  return request<Consolidation>(`${base(propertyId)}/debitos/consolidacao`)
}

export function listDebtQueries(propertyId: number): Promise<{ property_id: number; consultas: DebtQueryRow[] }> {
  return request(`${base(propertyId)}/debitos/consultas`)
}

export function runDebtQuery(propertyId: number, payload: Record<string, unknown>): Promise<unknown> {
  return request(`${base(propertyId)}/debitos/consultar`, jsonInit('POST', payload))
}

// v1.0.12: orientação da consulta manual assistida do IPTU do município do imóvel.
export type IptuGuidance = {
  property_id: number; municipality_id: number | null; inscricao_imobiliaria: string | null; motivo: string | null
  titular_matricula?: { nome: string | null; ato: string | null; texto: string; aviso: string } | null
  orientacao: {
    municipio: string; automatizado: boolean; modo: string; motivo: string; fonte?: string; orgao?: string; urls: string[]; identificador?: string
    exigencias?: string[]; login?: boolean; api_publica?: boolean; captcha_ou_bloqueio?: string; termos_uso?: string; passos: string[]; aviso?: string
  } | null
}

export function getIptuGuidance(propertyId: number): Promise<IptuGuidance> {
  return request<IptuGuidance>(`${base(propertyId)}/debitos/orientacao-iptu`)
}

// v1.0.12: estimativa condominial pelo período da matrícula (cenários baixo/provável/alto; regra da venda aplicada depois).
export type CondoScenario = {
  meses_em_atraso: number; fator: string | number; principal: string | number; multa: string | number; juros: string | number
  correcao: string | number; total: string | number; divida_potencial: string | number; responsabilidade_comprador: string | number
  responsabilidade_caixa: string | number; valor_no_financeiro: string | number | null
}
export type RegistryCondoEstimate = {
  possivel: boolean; motivo?: string; confianca: string; aviso: string; uso_no_financeiro?: string
  cenarios_detalhe?: { baixo: CondoScenario; provavel: CondoScenario; alto: CondoScenario }
  regra_venda?: { tipo: string | null; limite: string | number | null; origem: string | null }
  memoria_calculo: {
    valor_mensal_referencia: string | number | null; origem_valor_mensal: string | null; data_aquisicao: string | null; origem_data_aquisicao: string | null
    data_consolidacao: string | null; origem_data_consolidacao: string | null; periodo_meses?: number; periodo_considerado_meses?: number
    teto_periodo_meses: number; meses_desde_consolidacao?: number; formula: string; nota: string; idade_imovel?: string | null
  }
}

export function estimateCondominiumFromRegistry(
  propertyId: number,
  payload: { monthly_reference?: number; acquisition_date?: string; consolidation_date?: string; persist: boolean },
): Promise<{ property_id: number; estimativa: RegistryCondoEstimate; estimativa_id: number | null }> {
  return request(`${base(propertyId)}/debitos/estimar-condominio/matricula`, jsonInit('POST', payload))
}

export function estimateCondominium(
  propertyId: number,
  payload: Record<string, unknown>,
): Promise<{ property_id: number; estimativa: CondominiumEstimate; alertas_idade: AgeAlerts; estimativa_id: number | null }> {
  return request(`${base(propertyId)}/debitos/estimar-condominio`, jsonInit('POST', payload))
}
