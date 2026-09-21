import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Plus, RefreshCw, Scale } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section, Textarea } from '../components/ui'
import { createProcess, listProcesses, type LegalProcess } from '../services/processes'

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

  return (
    <Section title="Processos Jurídicos" description="Processos relacionados ao imóvel cadastrados manualmente." className="dossier-section" actions={<Button onClick={openForm}><Plus size={16} /> Novo processo</Button>}>
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
                {process.status && <Badge tone="warning" size="sm">{process.status}</Badge>}
              </div>
              <dl className="dossier-facts">
                <Fact label="Tribunal" value={process.court} />
                <Fact label="Comarca" value={process.comarca} />
                <Fact label="Natureza" value={process.nature} />
                <Fact label="Assunto" value={process.subject} />
                <Fact label="Polo ativo" value={process.polo_active} />
                <Fact label="Polo passivo" value={process.polo_passive} />
                <Fact label="Distribuição" value={formatDate(process.distribution_date)} />
                <Fact label="Fonte" value={process.source} />
                <Fact label="Impacto" value={process.impact} />
                <Fact label="Observações" value={process.observations} />
                {process.evidence_id != null && <Fact label="Evidência" value={`#${process.evidence_id}`} />}
              </dl>
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
