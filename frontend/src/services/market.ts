import { PropertiesServiceError } from './properties'

export type MarketComparable = {
  id: number
  property_id?: number
  kind: string
  price?: number | string
  rent?: number | string | null
  area_m2?: number | string
  source?: string
  url?: string
  created_at?: string
  price_type?: string | null
  collected_at?: string | null
  neighborhood?: string | null
  address?: string | null
  bedrooms?: number | null
  parking_spots?: number | null
  area_basis?: string | null
  excluded?: boolean | null
  exclusion_reason?: string | null
}

export type ComparableCreate = {
  kind: string
  price?: number
  rent?: number
  area_m2?: number
  source?: string
  url?: string
  // v1.0.8: rastreabilidade (todos opcionais)
  price_type?: 'ANUNCIADO' | 'TRANSACIONADO'
  collected_at?: string
  neighborhood?: string
  address?: string
  city?: string
  property_type?: string
  bedrooms?: number
  parking_spots?: number
  area_basis?: 'PRIVATIVA' | 'UTIL' | 'TOTAL' | 'DESCONHECIDA'
  notes?: string
}

// v1.0.12: OCUPADO_CONFIRMADO, OCUPADO_TERCEIROS e NAO_VERIFICADO somam-se aos status anteriores.
export type OccupancyStatus = 'OCUPADO' | 'OCUPADO_CONFIRMADO' | 'OCUPADO_TERCEIROS' | 'DESOCUPADO' | 'NAO_VERIFICADO' | 'DESCONHECIDO'

export type OccupancyVerification = { fonte: string; data?: string; observacao?: string; responsavel?: string }

export type Occupancy = {
  id: number
  property_id: number
  status: OccupancyStatus
  status_label?: string
  occupant_profile?: string | null
  estimated_cost?: number | string | null
  estimated_months?: number | null
  evidence_id?: number | null
  verificacao?: { evidence_id: number; fonte: string | null; data: string | null; responsavel: string | null; observacao: string | null } | null
  created_at?: string
  updated_at?: string
}

export type OccupancyCreate = {
  status: OccupancyStatus
  occupant_profile?: string
  estimated_cost?: number
  estimated_months?: number
  evidence_id?: number
  verificacao?: OccupancyVerification
}

export type PossibleOccupant = {
  nome: string; papeis: string[]
  origens: { documento: string | null; ato: string; tipo_ato: string; data: string | null; papel: string; como_identificado: string; trecho: string }[]
}
export type PossibleOccupantsResponse = {
  property_id: number; aviso: string; possiveis_ocupantes: PossibleOccupant[]; fonte: string | null; motivo: string | null; observacao: string
  situacao_registrada: { status: string; status_label: string } | null
}

export type OccupancyResponse = {
  property_id: number
  situacao_atual: Occupancy | null
  ultimo_registro: Occupancy | null
  historico: Occupancy[]
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

export async function listComparables(propertyId: number): Promise<MarketComparable[]> {
  const payload = await request<{ comparaveis: MarketComparable[] }>(`/api/imoveis/${propertyId}/comparaveis`)
  return payload.comparaveis ?? []
}

// Qualidade da amostra e fontes (Task 3): resumo determinístico do endpoint /mercado.
export type MarketQuality = {
  quantidade: number
  amostra_suficiente: boolean
  dispersao_elevada: boolean
  avaliacao_definitiva: boolean
  avisos: string[]
}

export type MarketSummary = {
  quantidade: number
  preco_medio?: number | string | null
  preco_mediano?: number | string | null
  preco_m2_medio?: number | string | null
  preco_m2_mediano?: number | string | null
  aluguel_medio?: number | string | null
  aluguel_mediano?: number | string | null
  qualidade?: MarketQuality
}

export type MarketResponse = {
  property_id: number
  mercado: {
    venda: MarketSummary
    aluguel: MarketSummary
    fontes?: Array<{ kind: string; source?: string; url?: string; data?: string }>
    observacao?: string
  }
}

export function getMarket(propertyId: number): Promise<MarketResponse> {
  return request<MarketResponse>(`/api/imoveis/${propertyId}/mercado`)
}

export function createComparable(propertyId: number, payload: ComparableCreate): Promise<MarketComparable> {
  return request<MarketComparable>(`/api/imoveis/${propertyId}/comparaveis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

// TASK 75.2: edição/exclusão de comparável. Recalcula a visão de mercado e o
// financeiro no backend (histórico before/after + evento). Análises não mudam.
export type ComparableUpdate = Partial<ComparableCreate>

export function updateComparable(propertyId: number, comparableId: number, payload: ComparableUpdate): Promise<{ comparavel: MarketComparable; mercado: MarketResponse['mercado'] }> {
  return request<{ comparavel: MarketComparable; mercado: MarketResponse['mercado'] }>(`/api/imoveis/${propertyId}/comparaveis/${comparableId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function deleteComparable(propertyId: number, comparableId: number): Promise<{ removido: number }> {
  return request<{ removido: number }>(`/api/imoveis/${propertyId}/comparaveis/${comparableId}`, { method: 'DELETE' })
}

// v1.0.8: inteligência de mercado e viabilidade (leitura determinística, sem IA).
type Num = number | string | null
export type IntelComparable = {
  id: number; valor: Num; area_m2: Num; valor_m2?: Num; valor_m2_ajustado?: Num; tipo_preco: string; similaridade: Num
  usado: boolean; motivo: string | null; fonte?: string | null; url?: string | null; consultado_em?: string | null; bairro?: string | null; endereco?: string | null
}
export type IntelEstimate = {
  tipo: 'VENDA' | 'ALUGUEL'; quantidade_usada: number; quantidade_total: number; quantidade_anunciada: number; confianca: string
  valor_estimado: Num; faixa: { min: Num; max: Num } | null; faixa_criterio: string | null; indicativa: boolean
  estatisticas_m2: Record<string, Num>; desconto_negociacao: Num; comparaveis: IntelComparable[]; avisos: string[]; limitacoes?: string[]
  /** v1.0.14: AMOSTRA INSUFICIENTE / BAIXA / MÉDIA / ALTA. */
  qualidade_amostra?: { nivel: string; label: string; quantidade: number; minimo_recomendado: number; texto: string }
}
export type IntelCost = {
  chave: string; descricao: string; valor: Num; status: string; origem: string; valor_conservador: Num; valor_base?: Num; observacao: string; critico: boolean
  tratamento_base?: string; tratamento_conservador?: string
  // Regra Caixa (condomínio e tributos em atraso)
  divida_total?: Num; responsabilidade_comprador?: Num; assumido_caixa?: Num; limite_responsabilidade?: Num; regra?: string | null
  premissa_conservadora?: string | null
  reserva_manual?: boolean; origem_reserva?: string; valores_anuais?: boolean
}
export type IntelReserveImpact = {
  chave: string; descricao: string; reserva: Num; base_valor: string | null; tipo: string
  efeito_investimento: Num; efeito_resultado: Num; efeito_roi: Num; efeito_preco_maximo: Num
}
export type IntelCompositionItem = {
  chave: string; descricao: string; valor: Num; status: string; incluido: boolean; base_valor: string | null; origem: string; dedutivel_ir: boolean
  teto_conservador?: Num; tipo_valor?: string
}
export type IntelComposition = {
  itens: IntelCompositionItem[]; investimento_total: Num; formula: string
  itens_dedutiveis_ir?: { descricao: string; valor: Num }[]; itens_nao_dedutiveis_ir?: { descricao: string; valor: Num }[]
  despesas_financeiras: { valor: Num; observacao: string }
  venda_bruta?: Num; corretagem_venda?: { valor: Num; percentual: Num; origem: string }; venda_liquida?: Num
  custo_aquisicao_dedutivel_ir?: Num; base_ir?: Num; ir_ganho_capital?: { valor: Num; aliquota: Num; origem: string; observacao: string }
  resultado_liquido?: Num; venda_equilibrio?: Num
}
export type IntelScenario = {
  cenario: string; valor_venda: Num; prazo_meses: number; investimento_total: Num; resultado_liquido: Num; roi: Num; margem_seguranca: Num
  desconto_sobre_mercado: Num; custos_pendentes_nao_incluidos: string[]; corretagem_venda?: Num; tributo_venda?: Num; venda_equilibrio?: Num
  composicao?: IntelComposition
  completo?: boolean
  premissas?: { tratamento_pendencias: string[]; prazo_meses: number; corretagem_venda: Num; ir_ganho_capital: Num }
  efeito_pendencias_no_teto?: {
    itens: string[]; valor: Num; resultado_se_no_teto: Num; resultado_atual?: Num; ir_atual?: Num; ir_se_no_teto?: Num; ir_adicional?: Num
    conferencia?: string; sem_teto_conhecido?: string[]
    detalhe?: { chave: string; descricao: string; valor: Num; dedutivel_ir: boolean; tipo: 'TETO_CAIXA' | 'RESERVA'; origem?: string | null }[]
  }
  impacto_reservas?: IntelReserveImpact[]
  rentabilidade_aluguel?: IntelRental
}
export type IntelRental = {
  aluguel_mensal: Num; aluguel_indicativo?: boolean; investimento_base?: Num; receita_bruta_anual?: Num; receita_com_vacancia?: Num
  taxa_administracao?: Num; condominio_na_vacancia?: Num; iptu_na_vacancia?: Num; resultado_anual_antes_ir?: Num
  bruta_anual: Num; liquida_anual: Num; premissas: string; completa: boolean; pendencias?: string[]
}
export type IntelMaxPrice = {
  cenario: string; preco_maximo: Num; definitivo: boolean; provisorio: boolean; razao: string; pendencias: string[]; roi_no_teto?: Num
  com_pendencias_no_teto?: { preco_maximo: Num; roi_no_teto?: Num; itens: string[]; sem_teto_conhecido: string[] }
}
export type VendaPreliminar = {
  valor: Num; avaliacao: Num; fator: Num; fator_origem: string; selo: string; confianca: string; observacao: string; formula: string
}
export type MarketIntelligence = {
  property_id: number; data_calculo: string
  venda: IntelEstimate; aluguel: IntelEstimate
  liquidez: { classificacao: string; confianca: string; justificativa: string[]; prazo_observacao: string }
  valores: {
    valor_mercado_estimado: Num; faixa_venda: { min: Num; max: Num } | null; aluguel_estimado: Num; aluguel_indicativo: boolean; faixa_aluguel: { min: Num; max: Num } | null
    preco_m2_anunciado_mediana: Num; preco_m2_estimado_mediana: Num; desconto_sobre_avaliacao: Num; desconto_sobre_mercado: Num; observacao_descontos: string
    /** v1.0.12: valor de venda preliminar (avaliação × fator) usado só sem valor informado e sem comparáveis. */
    venda_preliminar?: VendaPreliminar | null
  }
  custos: IntelCost[]
  carregamento_mensal: { valor: Num; origem: string | null }
  cenarios: IntelScenario[]
  preco_maximo: { recomendado: Num; criterio: string; provisorio: boolean; por_cenario?: Record<string, IntelMaxPrice> }
  premissas: Record<string, { valor: string; origem: string; descricao: string }>
  conclusao: { resultado: 'FAVORAVEL' | 'DESFAVORAVEL' | 'INCONCLUSIVO'; motivos: string[]; bloqueios: string[]; ressalvas?: string[] }
}

export function getMarketIntelligence(propertyId: number): Promise<MarketIntelligence> {
  return request<MarketIntelligence>(`/api/imoveis/${propertyId}/inteligencia-mercado`)
}

export function formatPercent(value?: number | string | null, digits = 1) {
  if (value === undefined || value === null || value === '') return 'Não calculado'
  const numeric = Number(value)
  return Number.isNaN(numeric) ? String(value) : `${(numeric * 100).toFixed(digits).replace('.', ',')}%`
}

export function getPossibleOccupants(propertyId: number): Promise<PossibleOccupantsResponse> {
  return request<PossibleOccupantsResponse>(`/api/imoveis/${propertyId}/ocupacao/possiveis-ocupantes`)
}

export function getOccupancy(propertyId: number): Promise<OccupancyResponse> {
  return request<OccupancyResponse>(`/api/imoveis/${propertyId}/ocupacao`)
}

export function createOccupancy(propertyId: number, payload: OccupancyCreate): Promise<Occupancy> {
  return request<Occupancy>(`/api/imoveis/${propertyId}/ocupacao`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function formatMoney(value?: number | string | null) {
  if (value === undefined || value === null || value === '') return 'Não informado'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(numeric)
}
