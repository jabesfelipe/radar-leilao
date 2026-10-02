import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { ListPlus, Pencil, Plus, RefreshCw, Scale, Search } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section, Textarea } from '../components/ui'
import {
  addProcessMovement, createProcess, linkJudicialProcess, listProcesses, searchJudicial, updateProcess,
  type JudicialSearchResult, type LegalProcess,
} from '../services/processes'

// Mapeia o nível de correlação para o tom visual do Badge (reutiliza o design system).
function correlationTone(level?: string | null): 'danger' | 'warning' | 'info' | 'neutral' {
  switch ((level || '').toUpperCase()) {
    case 'ALTA': return 'danger'
    case 'MEDIA': return 'warning'
    case 'BAIXA': return 'info'
    default: return 'neutral'
  }
}

function correlationLabel(level?: string | null): string {
  const v = (level || '').toUpperCase()
  return v === 'NAO_CONFIRMADA' ? 'NÃO CONFIRMADA' : v || 'NÃO CONFIRMADA'
}

function originLabel(origin?: string | null): string {
  const v = (origin || '').toUpperCase()
  return v === 'NAO_CONFIRMADA' ? 'NÃO CONFIRMADA' : v || '—'
}

type ProcessSectionProps = {
  propertyId: number
}

type ProcessForm = {
  number: string
  court: string
  comarca: string
  nature: string
  subject: string
  status: string
  polo_active: string
  polo_passive: string
  distribution_date: string
  source: string
  impact: string
  observations: string
}

const initialForm: ProcessForm = {
  number: '',
  court: '',
  comarca: '',
  nature: '',
  subject: '',
  status: '',
  polo_active: '',
  polo_passive: '',
  distribution_date: '',
  source: '',
  impact: '',
  observations: '',
}

function formatDate(value?: string | null) {
  if (!value) return 'Não informada'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR')
}

function optional(value: string) {
  const trimmed = value.trim()
  return trimmed ? trimmed : undefined
}

export function ProcessSection({ propertyId }: ProcessSectionProps) {
  const [processes, setProcesses] = useState<LegalProcess[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<ProcessForm>(initialForm)
  const [fieldError, setFieldError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Pesquisa judicial (Judicial API).
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchCriteria, setSearchCriteria] = useState({ process_number: '', cpf: '', cnpj: '', name: '' })
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [searchResult, setSearchResult] = useState<JudicialSearchResult | null>(null)
  const [linkingId, setLinkingId] = useState<number | null>(null)

  // TASK 75.2: edição cadastral do processo + movimentação append-only.
  const [editId, setEditId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<ProcessForm>(initialForm)
  const [movementFor, setMovementFor] = useState<number | null>(null)
  const [movementDesc, setMovementDesc] = useState('')

  const loadProcesses = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setProcesses(await listProcesses(propertyId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os processos.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadProcesses() }, [loadProcesses])

  const openForm = () => {
    setForm(initialForm)
    setFieldError('')
    setSaveError('')
    setSuccessMessage('')
    setFormOpen(true)
  }

  const updateField = (field: keyof ProcessForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    if (field === 'number') setFieldError('')
    setSaveError('')
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!form.number.trim()) {
      setFieldError('Informe o número do processo.')
      return
    }
    setSaving(true)
    setSaveError('')
    setSuccessMessage('')
    try {
      const created = await createProcess(propertyId, {
        number: form.number.trim(),
        court: optional(form.court),
        comarca: optional(form.comarca),
        nature: optional(form.nature),
        subject: optional(form.subject),
        status: optional(form.status),
        polo_active: optional(form.polo_active),
        polo_passive: optional(form.polo_passive),
        distribution_date: form.distribution_date || undefined,
        source: optional(form.source),
        impact: optional(form.impact),
        observations: optional(form.observations),
      })
      setProcesses((current) => [...current, created])
      setFormOpen(false)
      setForm(initialForm)
      setSuccessMessage('Processo cadastrado com sucesso.')
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível cadastrar o processo.')
    } finally {
      setSaving(false)
    }
  }

  const handleSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const hasCriteria = Object.values(searchCriteria).some((v) => v.trim())
    if (!hasCriteria) {
      setSearchError('Informe ao menos um critério (número do processo, CPF, CNPJ ou nome).')
      return
    }
    setSearching(true)
    setSearchError('')
    setSearchResult(null)
    try {
      const result = await searchJudicial(propertyId, {
        process_number: optional(searchCriteria.process_number),
        cpf: optional(searchCriteria.cpf),
        cnpj: optional(searchCriteria.cnpj),
        name: optional(searchCriteria.name),
      })
      setSearchResult(result)
      await loadProcesses()
    } catch (cause) {
      setSearchError(cause instanceof Error ? cause.message : 'Não foi possível pesquisar processos.')
    } finally {
      setSearching(false)
    }
  }

  const handleLink = async (processId: number) => {
    setLinkingId(processId)
    setSaveError('')
    try {
      await linkJudicialProcess(propertyId, processId, { link_origin: 'VALIDADA' })
      await loadProcesses()
      setSuccessMessage('Processo vinculado ao imóvel (validado).')
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível vincular o processo.')
    } finally {
      setLinkingId(null)
    }
  }

  const beginEdit = (p: LegalProcess) => {
    setEditId(p.id)
    setEditForm({
      number: p.number, court: p.court || '', comarca: p.comarca || '', nature: p.nature || '',
      subject: p.subject || '', status: p.status || '', polo_active: p.polo_active || '',
      polo_passive: p.polo_passive || '', distribution_date: p.distribution_date || '',
      source: p.source || '', impact: p.impact || '', observations: p.observations || '',
    })
    setSaveError(''); setSuccessMessage('')
  }

  const submitEdit = async (event: FormEvent<HTMLFormElement>, id: number) => {
    event.preventDefault()
    setSaving(true); setSaveError(''); setSuccessMessage('')
    try {
      const { processo } = await updateProcess(propertyId, id, {
        number: editForm.number.trim(), court: optional(editForm.court), comarca: optional(editForm.comarca),
        nature: optional(editForm.nature), subject: optional(editForm.subject), status: optional(editForm.status),
        polo_active: optional(editForm.polo_active), polo_passive: optional(editForm.polo_passive),
        distribution_date: editForm.distribution_date || undefined, source: optional(editForm.source),
        impact: optional(editForm.impact), observations: optional(editForm.observations),
      })
      setProcesses((cur) => cur.map((p) => (p.id === id ? processo : p)))
      setEditId(null)
      setSuccessMessage('Processo atualizado. O histórico registra a alteração.')
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível atualizar o processo.')
    } finally {
      setSaving(false)
    }
  }

  const submitMovement = async (event: FormEvent<HTMLFormElement>, id: number) => {
    event.preventDefault()
    if (!movementDesc.trim()) return
    setSaving(true); setSaveError(''); setSuccessMessage('')
    try {
      await addProcessMovement(propertyId, id, { description: movementDesc.trim() })
      setMovementFor(null); setMovementDesc('')
      setSuccessMessage('Movimentação adicionada (novo registro — histórico preservado).')
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível adicionar a movimentação.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Processos Jurídicos" description="Pesquise processos pela Judicial API e acompanhe o dossiê jurídico do imóvel." className="dossier-section" actions={<><Button variant="secondary" onClick={() => { setSearchOpen((v) => !v); setSearchError('') }}><Search size={16} /> Pesquisar processos</Button><Button onClick={openForm}><Plus size={16} /> Novo processo</Button></>}>
      {searchOpen && (
        <Card variant="elevated" padding="lg" className="dossier-form-card">
          <form className="dossier-form" onSubmit={handleSearch} noValidate>
            <Input label="Número do processo" value={searchCriteria.process_number} onChange={(e) => setSearchCriteria((c) => ({ ...c, process_number: e.target.value }))} />
            <Input label="Nome da parte" value={searchCriteria.name} onChange={(e) => setSearchCriteria((c) => ({ ...c, name: e.target.value }))} />
            <Input label="CPF" value={searchCriteria.cpf} onChange={(e) => setSearchCriteria((c) => ({ ...c, cpf: e.target.value }))} />
            <Input label="CNPJ" value={searchCriteria.cnpj} onChange={(e) => setSearchCriteria((c) => ({ ...c, cnpj: e.target.value }))} />
            <div className="dossier-form-actions">
              {searchError && <Alert tone="danger">{searchError}</Alert>}
              <Button type="submit" loading={searching}><Search size={16} /> Pesquisar</Button>
            </div>
          </form>
          {searchResult && (
            searchResult.disponivel === false ? (
              <Alert tone="warning" title="Judicial API indisponível">{searchResult.mensagem || 'A consulta não pôde ser concluída agora; a análise do imóvel não foi interrompida.'}</Alert>
            ) : (
              <div className="judicial-search-summary">
                <Alert tone="info" title="Pesquisa judicial concluída">
                  {(searchResult.fontes?.length ?? 0)} fonte(s) consultada(s) · {(searchResult.processos_criados ?? 0) + (searchResult.processos_atualizados ?? 0)} processo(s) · {searchResult.processos_relevantes ?? 0} relevante(s) · {searchResult.sinais_criados ?? 0} sinal(is) jurídico(s).
                  {searchResult.search_id ? ` Pesquisa ${searchResult.search_id}.` : ''}
                </Alert>
                {!!(searchResult.avisos && searchResult.avisos.length) && (
                  <Alert tone="warning" title="Fontes com aviso/parciais">{searchResult.avisos.join(' · ')}</Alert>
                )}
              </div>
            )
          )}
        </Card>
      )}

      {successMessage && <Alert tone="success" title="Cadastro concluído" className="dossier-feedback">{successMessage}</Alert>}

      {formOpen && (
        <Card variant="elevated" padding="lg" className="dossier-form-card">
          <form className="dossier-form" onSubmit={handleSubmit} noValidate>
            <Input label="Número do processo" placeholder="Ex.: 0001234-56.2026.8.26.0100" value={form.number} onChange={(event) => updateField('number', event.target.value)} error={fieldError} required className="dossier-form-full" />
            <Input label="Tribunal (opcional)" value={form.court} onChange={(event) => updateField('court', event.target.value)} />
            <Input label="Comarca (opcional)" value={form.comarca} onChange={(event) => updateField('comarca', event.target.value)} />
            <Input label="Natureza (opcional)" value={form.nature} onChange={(event) => updateField('nature', event.target.value)} />
            <Input label="Assunto (opcional)" value={form.subject} onChange={(event) => updateField('subject', event.target.value)} />
            <Input label="Status (opcional)" value={form.status} onChange={(event) => updateField('status', event.target.value)} />
            <Input label="Data de distribuição (opcional)" type="date" value={form.distribution_date} onChange={(event) => updateField('distribution_date', event.target.value)} />
            <Input label="Polo ativo (opcional)" value={form.polo_active} onChange={(event) => updateField('polo_active', event.target.value)} />
            <Input label="Polo passivo (opcional)" value={form.polo_passive} onChange={(event) => updateField('polo_passive', event.target.value)} />
            <Input label="Fonte (opcional)" value={form.source} onChange={(event) => updateField('source', event.target.value)} />
            <Textarea label="Impacto (opcional)" value={form.impact} onChange={(event) => updateField('impact', event.target.value)} className="dossier-form-full" />
            <Textarea label="Observações (opcional)" value={form.observations} onChange={(event) => updateField('observations', event.target.value)} className="dossier-form-full" />
            <div className="dossier-form-actions">
              {saveError && <Alert tone="danger">{saveError}</Alert>}
              <Button variant="ghost" type="button" onClick={() => setFormOpen(false)} disabled={saving}>Cancelar</Button>
              <Button type="submit" loading={saving}>Salvar processo</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingState label="Carregando processos…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadProcesses()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : processes.length === 0 ? (
        <Card padding="none"><EmptyState title="Nenhum processo cadastrado" description="Cadastre processos relacionados para acompanhar o dossiê jurídico." icon={<Scale size={24} />} action={<Button onClick={openForm}><Plus size={16} /> Novo processo</Button>} /></Card>
      ) : (
        <div className="process-list">
          {processes.map((process) => (
            <Card key={process.id} padding="lg" className="process-card">
              <div className="process-card-head">
                <div>
                  <p className="eyebrow">PROCESSO</p>
                  <h3>{process.number}</h3>
                </div>
                <div className="process-card-badges">
                  {process.correlation_level && (
                    <Badge tone={correlationTone(process.correlation_level)} size="sm">Correlação: {correlationLabel(process.correlation_level)}</Badge>
                  )}
                  {process.status && <Badge tone="warning" size="sm">{process.status}</Badge>}
                </div>
              </div>
              {editId === process.id ? (
                <form className="dossier-form" onSubmit={(e) => void submitEdit(e, process.id)} noValidate>
                  <Input label="Número do processo" value={editForm.number} onChange={(e) => setEditForm((f) => ({ ...f, number: e.target.value }))} required className="dossier-form-full" />
                  <Input label="Tribunal" value={editForm.court} onChange={(e) => setEditForm((f) => ({ ...f, court: e.target.value }))} />
                  <Input label="Comarca" value={editForm.comarca} onChange={(e) => setEditForm((f) => ({ ...f, comarca: e.target.value }))} />
                  <Input label="Natureza" value={editForm.nature} onChange={(e) => setEditForm((f) => ({ ...f, nature: e.target.value }))} />
                  <Input label="Assunto" value={editForm.subject} onChange={(e) => setEditForm((f) => ({ ...f, subject: e.target.value }))} />
                  <Input label="Status" value={editForm.status} onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value }))} />
                  <Input label="Data de distribuição" type="date" value={editForm.distribution_date} onChange={(e) => setEditForm((f) => ({ ...f, distribution_date: e.target.value }))} />
                  <Input label="Polo ativo" value={editForm.polo_active} onChange={(e) => setEditForm((f) => ({ ...f, polo_active: e.target.value }))} />
                  <Input label="Polo passivo" value={editForm.polo_passive} onChange={(e) => setEditForm((f) => ({ ...f, polo_passive: e.target.value }))} />
                  <Input label="Fonte" value={editForm.source} onChange={(e) => setEditForm((f) => ({ ...f, source: e.target.value }))} />
                  <Textarea label="Impacto" value={editForm.impact} onChange={(e) => setEditForm((f) => ({ ...f, impact: e.target.value }))} className="dossier-form-full" />
                  <Textarea label="Observações" value={editForm.observations} onChange={(e) => setEditForm((f) => ({ ...f, observations: e.target.value }))} className="dossier-form-full" />
                  <div className="dossier-form-actions">
                    {saveError && <Alert tone="danger">{saveError}</Alert>}
                    <Button variant="ghost" type="button" onClick={() => setEditId(null)} disabled={saving}>Cancelar</Button>
                    <Button type="submit" loading={saving}>Salvar alterações</Button>
                  </div>
                </form>
              ) : (
                <>
                  <dl className="dossier-facts">
                    <Fact label="Tribunal" value={process.court} />
                    <Fact label="Comarca" value={process.comarca} />
                    <Fact label="Natureza" value={process.nature} />
                    <Fact label="Assunto" value={process.subject} />
                    <Fact label="Polo ativo" value={process.polo_active} />
                    <Fact label="Polo passivo" value={process.polo_passive} />
                    <Fact label="Distribuição" value={formatDate(process.distribution_date)} />
                    <Fact label="Fonte" value={process.source} />
                    <Fact label="Vínculo" value={process.link_origin ? originLabel(process.link_origin) : null} />
                    <Fact label="Impacto" value={process.impact} />
                    <Fact label="Observações" value={process.observations} />
                    {process.evidence_id != null && <Fact label="Evidência" value={`#${process.evidence_id}`} />}
                  </dl>
                  {movementFor === process.id && (
                    <form className="dossier-form" onSubmit={(e) => void submitMovement(e, process.id)} noValidate>
                      <Input label="Nova movimentação (andamento)" value={movementDesc} onChange={(e) => setMovementDesc(e.target.value)} required className="dossier-form-full" />
                      <div className="dossier-form-actions">
                        <Button variant="ghost" type="button" onClick={() => { setMovementFor(null); setMovementDesc('') }}>Cancelar</Button>
                        <Button type="submit" loading={saving}>Adicionar movimentação</Button>
                      </div>
                    </form>
                  )}
                  <div className="process-card-actions">
                    <Button variant="ghost" size="sm" onClick={() => beginEdit(process)}><Pencil size={14} /> Editar</Button>
                    <Button variant="ghost" size="sm" onClick={() => { setMovementFor(process.id); setMovementDesc('') }}><ListPlus size={14} /> Movimentação</Button>
                    <Button variant="secondary" size="sm" loading={linkingId === process.id} onClick={() => void handleLink(process.id)}>Vincular ao imóvel</Button>
                  </div>
                </>
              )}
            </Card>
          ))}
        </div>
      )}
    </Section>
  )
}

function Fact({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value || 'Não informado'}</dd>
    </div>
  )
}
