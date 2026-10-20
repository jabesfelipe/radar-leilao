import { PropertiesServiceError } from './properties'

// ---- Tipos (espelham o JSON do backend) ------------------------------------
export type PostAuction = {
  id: number
  property_id: number
  status: string
  current_stage?: string | null
  eviction_mode?: string | null
  initial_budget?: number | string | null
  expected_sale_value?: number | string | null
  observations?: string | null
  activated_at?: string | null
  closed_at?: string | null
}

export type PostStage = {
  id: number
  property_id: number
  stage_key: string
  title: string
  sort_order: number
  status: string
  responsible?: string | null
  planned_date?: string | null
  actual_date?: string | null
  observations?: string | null
  legal_process_id?: number | null
}

export type PostCost = {
  id: number
  property_id: number
  category: string
  description?: string | null
  planned_amount?: number | string | null
  actual_amount?: number | string | null
  status: string
  competence_date?: string | null
  payment_date?: string | null
  supplier?: string | null
  payment_method?: string | null
  origin?: string | null
  stage_id?: number | null
  observations?: string | null
}

export type ContactAttempt = {
  id: number
  attempt_date?: string | null
  channel?: string | null
  result?: string | null
  next_action?: string | null
  next_action_date?: string | null
  observations?: string | null
}

export type OccupantContact = {
  id: number
  property_id: number
  name: string
  phone?: string | null
  email?: string | null
  contact_type?: string | null
  relationship_label?: string | null
  next_action?: string | null
  next_action_date?: string | null
  observations?: string | null
  tentativas?: ContactAttempt[]
}

export type ConsultancyProposal = {
  id: number
  title: string
  fixed_fee?: number | string | null
  variable_fee?: string | null
  additional_costs?: number | string | null
  payment_schedule?: string | null
  included_scope?: string | null
  excluded_scope?: string | null
  deadline_days?: number | null
  observations?: string | null
}

export type Consultancy = {
  id: number
  property_id: number
  company_name: string
  cnpj?: string | null
  responsible?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  services?: string | null
  status: string
  selected: boolean
  observations?: string | null
  propostas?: ConsultancyProposal[]
}

export type NotificationVersion = {
  id: number
  version: number
  body: string
  status: string
}

export type NotificationDraft = {
  id: number
  property_id: number
  template_key?: string | null
  title: string
  recipient?: string | null
  notifier?: string | null
  status: string
  current_version: number
  delivery_channel?: string | null
  sent_at?: string | null
  receipt_status?: string | null
  receipt_reference?: string | null
  observations?: string | null
  versoes?: NotificationVersion[]
}

export type PostAuctionSummary = {
  ativado: boolean
  status?: string | null
  orcamento_inicial?: number | string | null
  valor_venda_estimado?: number | string | null
  previsto_total?: number | string | null
  realizado_total?: number | string | null
  pendente_total?: number | string | null
  variacao_previsto_realizado?: number | string | null
  custo_total_acumulado?: number | string | null
  lucro_estimado?: number | string | null
  roi_estimado?: number | string | null
  qtd_custos?: number
}

export type PostAuctionOverview = {
  property_id: number
  ativado: boolean
  pos_arrematacao: PostAuction | null
  etapas: PostStage[]
  custos: PostCost[]
  contatos: OccupantContact[]
  consultorias: Consultancy[]
  minutas: NotificationDraft[]
  resumo_financeiro: PostAuctionSummary
  financeiro_analise?: Record<string, unknown>
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

const base = (propertyId: number) => `/api/imoveis/${propertyId}/pos-arrematacao`

export function getPostAuction(propertyId: number): Promise<PostAuctionOverview> {
  return request<PostAuctionOverview>(base(propertyId))
}

export function activatePostAuction(propertyId: number, payload: Record<string, unknown>): Promise<unknown> {
  return request(`${base(propertyId)}/ativar`, jsonInit('POST', payload))
}

export function updatePostAuction(propertyId: number, payload: Record<string, unknown>): Promise<unknown> {
  return request(base(propertyId), jsonInit('PATCH', payload))
}

export function addStage(propertyId: number, payload: Record<string, unknown>): Promise<PostStage> {
  return request<PostStage>(`${base(propertyId)}/etapas`, jsonInit('POST', payload))
}

export function updateStage(propertyId: number, stageId: number, payload: Record<string, unknown>): Promise<unknown> {
  return request(`${base(propertyId)}/etapas/${stageId}`, jsonInit('PATCH', payload))
}

export function deleteStage(propertyId: number, stageId: number): Promise<unknown> {
  return request(`${base(propertyId)}/etapas/${stageId}`, { method: 'DELETE' })
}

export function addPostCost(propertyId: number, payload: Record<string, unknown>): Promise<unknown> {
  return request(`${base(propertyId)}/custos`, jsonInit('POST', payload))
}

export function updatePostCost(propertyId: number, costId: number, payload: Record<string, unknown>): Promise<unknown> {
  return request(`${base(propertyId)}/custos/${costId}`, jsonInit('PATCH', payload))
}

export function deletePostCost(propertyId: number, costId: number): Promise<unknown> {
  return request(`${base(propertyId)}/custos/${costId}`, { method: 'DELETE' })
}

export function addContact(propertyId: number, payload: Record<string, unknown>): Promise<OccupantContact> {
  return request<OccupantContact>(`${base(propertyId)}/contatos`, jsonInit('POST', payload))
}

export function addContactAttempt(propertyId: number, contactId: number, payload: Record<string, unknown>): Promise<OccupantContact> {
  return request<OccupantContact>(`${base(propertyId)}/contatos/${contactId}/tentativas`, jsonInit('POST', payload))
}

export function addConsultancy(propertyId: number, payload: Record<string, unknown>): Promise<Consultancy> {
  return request<Consultancy>(`${base(propertyId)}/consultorias`, jsonInit('POST', payload))
}

export function addProposal(propertyId: number, consultancyId: number, payload: Record<string, unknown>): Promise<Consultancy> {
  return request<Consultancy>(`${base(propertyId)}/consultorias/${consultancyId}/propostas`, jsonInit('POST', payload))
}

export function addNotificationDraft(propertyId: number, payload: Record<string, unknown>): Promise<NotificationDraft> {
  return request<NotificationDraft>(`${base(propertyId)}/notificacoes`, jsonInit('POST', payload))
}

export function addNotificationVersion(propertyId: number, draftId: number, payload: Record<string, unknown>): Promise<NotificationDraft> {
  return request<NotificationDraft>(`${base(propertyId)}/notificacoes/${draftId}/versoes`, jsonInit('POST', payload))
}

export function updateNotificationDraft(propertyId: number, draftId: number, payload: Record<string, unknown>): Promise<NotificationDraft> {
  return request<NotificationDraft>(`${base(propertyId)}/notificacoes/${draftId}`, jsonInit('PATCH', payload))
}
