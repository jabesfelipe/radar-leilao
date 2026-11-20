// Resumo do investimento e riscos consolidados (v1.0.14). Somente leitura; nada é calculado no frontend.
import { PropertiesServiceError } from './properties'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`)
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

type Num = number | string | null | undefined

/** Tipo do dado (rastreabilidade): fato, dado manual, estimativa, inferência ou desconhecido. */
export type DataType = 'FATO' | 'DADO_MANUAL' | 'ESTIMATIVA' | 'INFERENCIA' | 'DESCONHECIDO' | string
export type TracedValue = { valor: Num; tipo: DataType; tipo_label: string; origem?: string | null; texto?: string | null; provisorio?: boolean }

export type RiskSituation = 'CONFIRMADO' | 'POSSIVEL' | 'PENDENTE_CONFIRMACAO' | 'RESOLVIDO' | 'NAO_IDENTIFICADO' | string
export type ConsolidatedRisk = {
  chave: string
  categoria: string
  titulo: string
  o_que_significa: string
  detalhe?: string | null
  situacao: RiskSituation
  situacao_label: string
  gravidade?: string | null
  gravidade_label?: string | null
  impactos: string[]
  estimativa: { texto: string | null; valor_base: Num; valor_conservador: Num; tipo: DataType }
  evidencia?: { documento?: string | null; pagina?: number | null; trecho?: string | null; texto: string } | null
  o_que_fazer: string[]
  por_que_importa?: string | null
  impacto_detalhe?: { financeiro: string | null; prazo: string | null; operacional: string | null; juridico: string | null }
  confianca?: string | null
  fonte?: string | null
  proxima_acao?: string | null
  mitigacao?: string | null
}
export type ConsolidatedRisks = {
  itens: ConsolidatedRisk[]
  contagem?: Record<string, number>
  principal?: string | null
  categorias?: string[]
  aviso?: string
}

export type IptuStatus = {
  status: 'CONSULTADO' | 'CONSULTA_ASSISTIDA' | 'PENDENTE_CONSULTA' | 'NAO_ENCONTRADO' | 'FALHA_CONSULTA' | 'NECESSITA_INFORMACAO' | string
  status_label: string
  texto: string
  automatico: boolean
  motivo_sem_automacao?: string | null
  portal?: { fonte?: string | null; orgao?: string | null; urls: string[]; identificador?: string | null; exigencias: string[]; passos: string[] } | null
  dados_necessarios: string[]
  inscricao_imobiliaria?: string | null
  debito_em_aberto: TracedValue
  sem_debito: boolean
  valor_anual: TracedValue
  aviso: string
  portal_pesquisado?: { url: string; titulo: string; dominio: string }[]
  lancamentos?: { exercicio?: string | number | null; valor_atualizado: Num; valor_original: Num; parcelado: boolean; status: string }[]
}

export type CondoAnalysis = {
  taxa_mensal: TracedValue & { status: string; status_label: string }
  estimativa_insuficiente: boolean
  texto: string
  referencias: { quantidade: number; media: Num; mediana: Num; faixa: { min: Num; max: Num; criterio: string }; mediana_por_m2_x_area: Num } | null
  confianca: string
  mesmo_predio: { quantidade: number; mediana: Num; status_label: string } | null
  divida_acumulada: { valor: Num; valor_base: Num; valor_conservador: Num; status?: string | null; origem?: string | null; tipo: DataType; tipo_label: string }
  taxa_extra: { status: string; texto: string }
  busca_automatica: { status: string; texto: string }
  aviso: string
}

export type MarketComparableRow = {
  id: number; link?: string | null; fonte?: string | null; valor: Num; area_m2: Num; valor_m2: Num; data_coleta?: string | null
  similaridade: Num; usado: boolean; motivo_exclusao?: string | null; bairro?: string | null; tipo_preco?: string | null
}
export type MarketBlock = {
  qualidade: { nivel: 'INSUFICIENTE' | 'BAIXA' | 'MEDIA' | 'ALTA' | string; label: string; quantidade: number; minimo_recomendado: number; texto: string }
  quantidade_usada: number; quantidade_total: number; valor_estimado: Num; faixa?: { min: Num; max: Num } | null; faixa_criterio?: string | null
  m2_media: Num; m2_mediana: Num; media_total: Num; mediana_total: Num; comparaveis: MarketComparableRow[]; avisos: string[]
}
export type MarketSummary = {
  venda: MarketBlock
  aluguel: MarketBlock
  valor_venda_usado: TracedValue
  aluguel_estimado: TracedValue
  yield_bruto_anual: { sobre_valor_mercado: Num; sobre_aquisicao: Num; texto: string }
  liquidez?: { classificacao: string; confianca: string; justificativa: string[] } | null
  busca_automatica: { status: string; texto: string }
  pesquisa?: { ativo: boolean; consultas: ResearchQuery[]; portais_iptu: { url: string; titulo: string; dominio: string }[] }
}

export type FinanceRow = { chave: string; descricao: string; valor: Num; valor_base: Num; valor_conservador: Num; origem?: string | null; motivo?: string; tipo?: DataType }
export type FinanceByNature = { confirmado: FinanceRow[]; estimado: FinanceRow[]; desconhecido: FinanceRow[]; nao_incluido: FinanceRow[]; texto: string }

export type InvestmentRecommendation = {
  codigo: 'FAVORAVEL' | 'ATENCAO_INVESTIGAR' | 'DESFAVORAVEL' | 'NAO_ARREMATAR' | string
  label: string
  arrematar: string
  motivos: string[]
  aviso_margem?: string | null
  veredito_motor?: string | null
}

export type ResearchQuery = { tipo: string; consulta: string; provedor: string; status: string; resultados: number; em?: string | null; erro?: string | null }
export type ResearchProviders = {
  ativo: boolean; status: string; texto?: string | null
  provedores: { papel: string; provedor: string | null; configurado: boolean; variavel?: string | null }[]
}
export type ResearchRun = {
  status: string; texto?: string | null; consultas: ResearchQuery[]
  comparaveis_criados: { id: number; tipo: string; valor: Num; area_m2: Num; url: string; fonte: string; confianca: string }[]
  descartados: { url: string; titulo: string; motivos: string[] }[]
  referencias_condominio: { valor: Num; url: string; fonte: string }[]
  portais_iptu: { url: string; titulo: string; dominio: string }[]
}
export type ScenarioView = {
  cenario: string
  premissas: { valor_venda: Num; valor_venda_origem?: string | null; prazo_meses?: number | null; reservas: string; custos_fora_da_soma: string[] }
  investimento_total: Num; resultado_liquido: Num; roi: Num; margem_seguranca: Num; completo?: boolean
}
export type PriorityItem = { chave: string; nome: string; prioridade: string; prioridade_label: string; status_label: string; proxima_acao?: string | null; responsavel?: string }

export type InvestmentSummary = {
  cenarios?: ScenarioView[]
  margem_seguranca?: TracedValue
  checklist?: { abertos_por_prioridade: Record<string, number>; bloqueadores_abertos: string[]; itens_prioritarios: PriorityItem[] }
  documentos?: { texto: string; obrigatorios_faltando: string[] }
  alertas?: string[]
  property_id: number
  recomendacao: InvestmentRecommendation
  numeros: Record<'lance' | 'preco_maximo' | 'valor_venda' | 'lucro_estimado' | 'roi' | 'margem' | 'investimento_total', TracedValue>
  principal_risco?: string | null
  pendencias: string[]
  proximas_acoes: Array<{ prioridade: number; tema: string; acao: string }>
  iptu: IptuStatus
  condominio: CondoAnalysis
  mercado: MarketSummary
  financeiro: FinanceByNature
  riscos: ConsolidatedRisks
}

const base = (propertyId: number) => `/api/imoveis/${propertyId}`

export function getInvestmentSummary(propertyId: number): Promise<InvestmentSummary> {
  return request<InvestmentSummary>(`${base(propertyId)}/resumo-investimento`)
}

export async function getConsolidatedRisks(propertyId: number): Promise<ConsolidatedRisks> {
  const payload = await request<Partial<ConsolidatedRisks> | null>(`${base(propertyId)}/riscos-consolidados`)
  return { ...(payload ?? {}), itens: payload?.itens ?? [] }
}

export async function runResearch(propertyId: number, tipos?: string[]): Promise<ResearchRun> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${base(propertyId)}/pesquisa-automatica`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tipos: tipos ?? null }),
    })
  } catch {
    throw new PropertiesServiceError('Não foi possível conectar ao servidor. Tente novamente.')
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new PropertiesServiceError(typeof payload?.detail === 'string' ? payload.detail : 'Não foi possível pesquisar.', response.status)
  return payload as ResearchRun
}

export function getResearchProviders(): Promise<ResearchProviders> {
  return request<ResearchProviders>('/api/pesquisa/provedores')
}

export function getIptuStatus(propertyId: number): Promise<IptuStatus> {
  return request<IptuStatus>(`${base(propertyId)}/iptu/situacao`)
}

export function formatMoney(value: Num): string {
  if (value === null || value === undefined || value === '') return 'Desconhecido'
  const n = typeof value === 'string' ? Number(value) : value
  return Number.isFinite(n) ? n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : String(value)
}

export function formatPercent(value: Num): string {
  if (value === null || value === undefined || value === '') return 'Desconhecido'
  const n = typeof value === 'string' ? Number(value) : value
  return Number.isFinite(n) ? `${(n * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%` : String(value)
}
