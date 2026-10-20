import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { PlayCircle, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section, Select, Textarea } from '../components/ui'
import {
  activatePostAuction, addConsultancy, addContact, addContactAttempt, addNotificationDraft,
  addNotificationVersion, addPostCost, addProposal, addStage, deletePostCost, deleteStage,
  getPostAuction, updateNotificationDraft, updatePostCost, updateStage,
  type PostAuctionOverview, type PostAuctionSummary,
} from '../services/postAuction'

type Props = { propertyId: number }

function money(value: number | string | null | undefined) {
  if (value === undefined || value === null || value === '') return 'Não informado'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n)
}

function percent(value: number | string | null | undefined) {
  if (value === undefined || value === null || value === '') return 'Não informado'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return `${(n * 100).toFixed(1)}%`
}

const costStatusTone: Record<string, 'neutral' | 'warning' | 'success' | 'danger'> = {
  PREVISTO: 'neutral', PENDENTE: 'warning', PAGO: 'success', CANCELADO: 'neutral', CONTESTADO: 'danger',
}

const stageStatusTone: Record<string, 'neutral' | 'warning' | 'success'> = {
  PENDENTE: 'neutral', EM_ANDAMENTO: 'warning', CONCLUIDA: 'success', NAO_APLICAVEL: 'neutral', BLOQUEADA: 'warning',
}

export function PostAuctionSection({ propertyId }: Props) {
  const [data, setData] = useState<PostAuctionOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)

  // formulários locais
  const [costForm, setCostForm] = useState({ category: '', description: '', planned_amount: '', actual_amount: '', status: 'PREVISTO', supplier: '' })
  const [costOpen, setCostOpen] = useState(false)
  const [contactForm, setContactForm] = useState({ name: '', phone: '', email: '', relationship_label: '' })
  const [contactOpen, setContactOpen] = useState(false)
  const [consultancyForm, setConsultancyForm] = useState({ company_name: '', cnpj: '', responsible: '' })
  const [consultancyOpen, setConsultancyOpen] = useState(false)
  const [draftForm, setDraftForm] = useState({ title: '', recipient: '', notifier: '', body: '' })
  const [draftOpen, setDraftOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await getPostAuction(propertyId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o pós-arrematação.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void load() }, [load])

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    setActionError('')
    try {
      await fn()
      await load()
      return true
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : 'Não foi possível concluir a operação.')
      return false
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <Section title="Pós-Arrematação" className="dossier-section"><LoadingState label="Carregando pós-arrematação…" /></Section>

  if (error) {
    return (
      <Section title="Pós-Arrematação" className="dossier-section">
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      </Section>
    )
  }

  // ---- Não ativado: CTA de ativação ----
  if (!data?.ativado) {
    return (
      <Section title="Pós-Arrematação" description="Acompanhe a execução real do investimento após a arrematação." className="dossier-section">
        <Card padding="none">
          <EmptyState
            title="Fluxo de pós-arrematação não iniciado"
            description="Imóveis apenas analisados seguem o fluxo atual. Ative o acompanhamento quando o imóvel entrar na fase de execução (pagamento, regularização, desocupação, reforma e venda)."
            icon={<PlayCircle size={24} />}
            action={<Button loading={busy} onClick={() => void run(() => activatePostAuction(propertyId, { seed_default_stages: true }))}><PlayCircle size={16} /> Ativar pós-arrematação</Button>}
          />
          {actionError && <Alert tone="danger" title="Falha na ativação">{actionError}</Alert>}
        </Card>
      </Section>
    )
  }

  const resumo = data.resumo_financeiro
  const pa = data.pos_arrematacao

  const submitCost = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const ok = await run(() => addPostCost(propertyId, {
      category: costForm.category.trim(),
      description: costForm.description.trim() || undefined,
      planned_amount: costForm.planned_amount.trim() ? Number(costForm.planned_amount) : undefined,
      actual_amount: costForm.actual_amount.trim() ? Number(costForm.actual_amount) : undefined,
      status: costForm.status,
      supplier: costForm.supplier.trim() || undefined,
    }))
    if (ok) { setCostOpen(false); setCostForm({ category: '', description: '', planned_amount: '', actual_amount: '', status: 'PREVISTO', supplier: '' }) }
  }

  const submitContact = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const ok = await run(() => addContact(propertyId, {
      name: contactForm.name.trim(),
      phone: contactForm.phone.trim() || undefined,
      email: contactForm.email.trim() || undefined,
      relationship_label: contactForm.relationship_label.trim() || undefined,
    }))
    if (ok) { setContactOpen(false); setContactForm({ name: '', phone: '', email: '', relationship_label: '' }) }
  }

  const submitConsultancy = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const ok = await run(() => addConsultancy(propertyId, {
      company_name: consultancyForm.company_name.trim(),
      cnpj: consultancyForm.cnpj.trim() || undefined,
      responsible: consultancyForm.responsible.trim() || undefined,
    }))
    if (ok) { setConsultancyOpen(false); setConsultancyForm({ company_name: '', cnpj: '', responsible: '' }) }
  }

  const submitDraft = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const ok = await run(() => addNotificationDraft(propertyId, {
      title: draftForm.title.trim(),
      recipient: draftForm.recipient.trim() || undefined,
      notifier: draftForm.notifier.trim() || undefined,
      body: draftForm.body,
    }))
    if (ok) { setDraftOpen(false); setDraftForm({ title: '', recipient: '', notifier: '', body: '' }) }
  }

  return (
    <Section title="Pós-Arrematação" description="Execução real do investimento. Os eventos aparecem também na linha do tempo (Histórico)." className="dossier-section">
      {actionError && <Alert tone="danger" title="Falha na operação" className="dossier-feedback">{actionError}</Alert>}

      {/* Situação e resumo financeiro consolidado */}
      <Card padding="lg" className="dossier-current">
        <div className="dossier-current-head">
          <div>
            <p className="eyebrow">SITUAÇÃO DA EXECUÇÃO</p>
            <h3>{pa?.status ?? 'EM_ANDAMENTO'}</h3>
          </div>
          <Badge tone="warning" size="md">{pa?.eviction_mode ? `Desocupação: ${pa.eviction_mode}` : 'Modalidade indefinida'}</Badge>
        </div>
        <FinanceSummary resumo={resumo} />
      </Card>

      {/* Etapas */}
      <Card padding="lg" className="dossier-current">
        <p className="eyebrow">ETAPAS OPERACIONAIS</p>
        {data.etapas.length === 0 ? (
          <p className="wizard-muted">Nenhuma etapa configurada.</p>
        ) : (
          <div className="dossier-timeline">
            {data.etapas.map((s) => (
              <div key={s.id} className="dossier-timeline-item">
                <span className="dossier-timeline-dot" />
                <div style={{ flex: 1 }}>
                  <strong>{s.title}</strong>
                  <span>{s.planned_date ? `Prevista: ${s.planned_date}` : 'Sem data prevista'}{s.actual_date ? ` · Efetiva: ${s.actual_date}` : ''}{s.responsible ? ` · ${s.responsible}` : ''}</span>
                </div>
                <Select aria-label={`Situação da etapa ${s.title}`} value={s.status} disabled={busy}
                  onChange={(e) => void run(() => updateStage(propertyId, s.id, { status: e.target.value }))}>
                  {['PENDENTE', 'EM_ANDAMENTO', 'CONCLUIDA', 'NAO_APLICAVEL', 'BLOQUEADA'].map((o) => <option key={o} value={o}>{o}</option>)}
                </Select>
                <Badge tone={stageStatusTone[s.status] ?? 'neutral'} size="sm">{s.status}</Badge>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Custos previsto/realizado/pago */}
      <Card padding="lg" className="dossier-current">
        <div className="dossier-current-head">
          <div><p className="eyebrow">CUSTOS PÓS-ARREMATAÇÃO</p></div>
          <Button size="sm" onClick={() => setCostOpen((v) => !v)}><Plus size={16} /> Novo custo</Button>
        </div>
        {costOpen && (
          <form className="dossier-form" onSubmit={submitCost} noValidate>
            <Input label="Categoria" value={costForm.category} onChange={(e) => setCostForm((c) => ({ ...c, category: e.target.value }))} required />
            <Input label="Descrição" value={costForm.description} onChange={(e) => setCostForm((c) => ({ ...c, description: e.target.value }))} />
            <Input label="Valor previsto" type="number" step="0.01" value={costForm.planned_amount} onChange={(e) => setCostForm((c) => ({ ...c, planned_amount: e.target.value }))} />
            <Input label="Valor realizado" type="number" step="0.01" value={costForm.actual_amount} onChange={(e) => setCostForm((c) => ({ ...c, actual_amount: e.target.value }))} />
            <Select label="Situação" value={costForm.status} onChange={(e) => setCostForm((c) => ({ ...c, status: e.target.value }))}>
              {['PREVISTO', 'PENDENTE', 'PAGO', 'CANCELADO', 'CONTESTADO'].map((o) => <option key={o} value={o}>{o}</option>)}
            </Select>
            <Input label="Fornecedor/beneficiário" value={costForm.supplier} onChange={(e) => setCostForm((c) => ({ ...c, supplier: e.target.value }))} />
            <div className="dossier-form-actions">
              <Button variant="ghost" type="button" onClick={() => setCostOpen(false)} disabled={busy}>Cancelar</Button>
              <Button type="submit" loading={busy}>Salvar custo</Button>
            </div>
          </form>
        )}
        {data.custos.length === 0 ? (
          <p className="wizard-muted">Nenhum custo pós-arrematação cadastrado.</p>
        ) : (
          <div className="finance-list">
            {data.custos.map((c) => (
              <div key={c.id} className="finance-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                <div>
                  <strong>{c.category}</strong>
                  <div className="wizard-muted">{c.description || 'Sem descrição'}{c.supplier ? ` · ${c.supplier}` : ''}</div>
                  <div className="wizard-muted">Previsto {money(c.planned_amount)} · Realizado {money(c.actual_amount)}</div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <Select aria-label={`Situação do custo ${c.category}`} value={c.status} disabled={busy}
                    onChange={(e) => void run(() => updatePostCost(propertyId, c.id, { status: e.target.value }))}>
                    {['PREVISTO', 'PENDENTE', 'PAGO', 'CANCELADO', 'CONTESTADO'].map((o) => <option key={o} value={o}>{o}</option>)}
                  </Select>
                  <Badge tone={costStatusTone[c.status] ?? 'neutral'} size="sm">{c.status}</Badge>
                  <Button variant="ghost" size="sm" disabled={busy} onClick={() => { if (window.confirm('Excluir este custo?')) void run(() => deletePostCost(propertyId, c.id)) }}><Trash2 size={14} /></Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Contatos do ocupante */}
      <Card padding="lg" className="dossier-current">
        <div className="dossier-current-head">
          <div><p className="eyebrow">OCUPANTE E CONTATOS</p></div>
          <Button size="sm" onClick={() => setContactOpen((v) => !v)}><Plus size={16} /> Novo contato</Button>
        </div>
        {contactOpen && (
          <form className="dossier-form" onSubmit={submitContact} noValidate>
            <Input label="Nome" value={contactForm.name} onChange={(e) => setContactForm((c) => ({ ...c, name: e.target.value }))} required />
            <Input label="Telefone" value={contactForm.phone} onChange={(e) => setContactForm((c) => ({ ...c, phone: e.target.value }))} />
            <Input label="E-mail" value={contactForm.email} onChange={(e) => setContactForm((c) => ({ ...c, email: e.target.value }))} />
            <Input label="Relação com o imóvel" value={contactForm.relationship_label} onChange={(e) => setContactForm((c) => ({ ...c, relationship_label: e.target.value }))} />
            <div className="dossier-form-actions">
              <Button variant="ghost" type="button" onClick={() => setContactOpen(false)} disabled={busy}>Cancelar</Button>
              <Button type="submit" loading={busy}>Salvar contato</Button>
            </div>
          </form>
        )}
        {data.contatos.length === 0 ? (
          <p className="wizard-muted">Nenhum contato cadastrado. Não se presume que o ocupante seja o antigo proprietário.</p>
        ) : (
          <div className="finance-list">
            {data.contatos.map((ct) => (
              <div key={ct.id} className="finance-card">
                <strong>{ct.name}</strong>
                <div className="wizard-muted">{[ct.phone, ct.email, ct.relationship_label].filter(Boolean).join(' · ') || 'Sem detalhes'}</div>
                <div className="wizard-muted">{(ct.tentativas?.length ?? 0)} tentativa(s) de contato</div>
                <Button variant="ghost" size="sm" disabled={busy} onClick={() => void run(() => addContactAttempt(propertyId, ct.id, { channel: 'TELEFONE', result: 'Sem resposta', attempt_date: new Date().toISOString().slice(0, 10) }))}>
                  <Plus size={14} /> Registrar tentativa
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Consultorias */}
      <Card padding="lg" className="dossier-current">
        <div className="dossier-current-head">
          <div><p className="eyebrow">CONSULTORIAS DE DESOCUPAÇÃO</p></div>
          <Button size="sm" onClick={() => setConsultancyOpen((v) => !v)}><Plus size={16} /> Nova consultoria</Button>
        </div>
        {consultancyOpen && (
          <form className="dossier-form" onSubmit={submitConsultancy} noValidate>
            <Input label="Empresa" value={consultancyForm.company_name} onChange={(e) => setConsultancyForm((c) => ({ ...c, company_name: e.target.value }))} required />
            <Input label="CNPJ" value={consultancyForm.cnpj} onChange={(e) => setConsultancyForm((c) => ({ ...c, cnpj: e.target.value }))} />
            <Input label="Responsável" value={consultancyForm.responsible} onChange={(e) => setConsultancyForm((c) => ({ ...c, responsible: e.target.value }))} />
            <div className="dossier-form-actions">
              <Button variant="ghost" type="button" onClick={() => setConsultancyOpen(false)} disabled={busy}>Cancelar</Button>
              <Button type="submit" loading={busy}>Salvar consultoria</Button>
            </div>
          </form>
        )}
        {data.consultorias.length === 0 ? (
          <p className="wizard-muted">Nenhuma consultoria cadastrada. Honorários advocatícios/custas judiciais não estão inclusos por padrão.</p>
        ) : (
          <div className="finance-list">
            {data.consultorias.map((co) => (
              <div key={co.id} className="finance-card">
                <strong>{co.company_name}{co.selected ? ' · selecionada' : ''}</strong>
                <div className="wizard-muted">{[co.responsible, co.cnpj].filter(Boolean).join(' · ') || 'Sem detalhes'} · {co.status}</div>
                <div className="wizard-muted">{(co.propostas?.length ?? 0)} proposta(s)</div>
                <Button variant="ghost" size="sm" disabled={busy} onClick={() => void run(() => addProposal(propertyId, co.id, { title: 'Proposta', fixed_fee: undefined }))}>
                  <Plus size={14} /> Adicionar proposta
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Minutas de notificação */}
      <Card padding="lg" className="dossier-current">
        <div className="dossier-current-head">
          <div><p className="eyebrow">NOTIFICAÇÕES EXTRAJUDICIAIS (MINUTAS)</p></div>
          <Button size="sm" onClick={() => setDraftOpen((v) => !v)}><Plus size={16} /> Nova minuta</Button>
        </div>
        {draftOpen && (
          <form className="dossier-form" onSubmit={submitDraft} noValidate>
            <Input label="Título" value={draftForm.title} onChange={(e) => setDraftForm((c) => ({ ...c, title: e.target.value }))} required />
            <Input label="Destinatário" value={draftForm.recipient} onChange={(e) => setDraftForm((c) => ({ ...c, recipient: e.target.value }))} />
            <Input label="Notificante" value={draftForm.notifier} onChange={(e) => setDraftForm((c) => ({ ...c, notifier: e.target.value }))} />
            <Textarea label="Texto da minuta (editável)" value={draftForm.body} onChange={(e) => setDraftForm((c) => ({ ...c, body: e.target.value }))} rows={5} />
            <div className="dossier-form-actions">
              <Button variant="ghost" type="button" onClick={() => setDraftOpen(false)} disabled={busy}>Cancelar</Button>
              <Button type="submit" loading={busy}>Salvar rascunho</Button>
            </div>
          </form>
        )}
        {data.minutas.length === 0 ? (
          <p className="wizard-muted">Nenhuma minuta criada. É uma minuta editável, não um parecer jurídico — o sistema não afirma validade ou recebimento sem comprovação.</p>
        ) : (
          <div className="finance-list">
            {data.minutas.map((d) => (
              <div key={d.id} className="finance-card">
                <strong>{d.title}</strong>
                <div className="wizard-muted">{[d.recipient, d.notifier].filter(Boolean).join(' · ') || 'Sem destinatário'} · v{d.current_version}</div>
                <Badge tone="neutral" size="sm">{d.status}</Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
    </Section>
  )
}

function FinanceSummary({ resumo }: { resumo: PostAuctionSummary }) {
  return (
    <dl className="dossier-facts">
      <SummaryFact label="Orçamento inicial (análise)" value={money(resumo.orcamento_inicial)} />
      <SummaryFact label="Total previsto atualizado" value={money(resumo.previsto_total)} />
      <SummaryFact label="Total pago (realizado)" value={money(resumo.realizado_total)} />
      <SummaryFact label="Compromissos pendentes" value={money(resumo.pendente_total)} />
      <SummaryFact label="Variação previsto × realizado" value={money(resumo.variacao_previsto_realizado)} />
      <SummaryFact label="Custo total acumulado" value={money(resumo.custo_total_acumulado)} />
      <SummaryFact label="Lucro estimado" value={money(resumo.lucro_estimado)} />
      <SummaryFact label="ROI estimado" value={percent(resumo.roi_estimado)} />
    </dl>
  )
}

function SummaryFact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}
