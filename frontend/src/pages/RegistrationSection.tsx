import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { FileSignature, Plus, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section, Textarea } from '../components/ui'
import { createRegistration, getRegistration, type PropertyRegistration } from '../services/registration'

type RegistrationSectionProps = {
  propertyId: number
}

type RegistrationForm = {
  registration_number: string
  registry_office: string
  comarca: string
  consultation_date: string
  holder: string
  observations: string
}

const initialForm: RegistrationForm = {
  registration_number: '',
  registry_office: '',
  comarca: '',
  consultation_date: '',
  holder: '',
  observations: '',
}

function formatDate(value?: string | null) {
  if (!value) return 'Não informado'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR')
}

export function RegistrationSection({ propertyId }: RegistrationSectionProps) {
  const [current, setCurrent] = useState<PropertyRegistration | null>(null)
  const [history, setHistory] = useState<PropertyRegistration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<RegistrationForm>(initialForm)
  const [fieldError, setFieldError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const loadRegistration = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getRegistration(propertyId)
      setCurrent(data.atual)
      setHistory(data.historico ?? [])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar a matrícula.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadRegistration() }, [loadRegistration])

  const openForm = () => {
    setForm(initialForm)
    setFieldError('')
    setSaveError('')
    setSuccessMessage('')
    setFormOpen(true)
  }

  const updateField = (field: keyof RegistrationForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    if (field === 'registration_number') setFieldError('')
    setSaveError('')
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!form.registration_number.trim()) {
      setFieldError('Informe o número da matrícula.')
      return
    }
    setSaving(true)
    setSaveError('')
    setSuccessMessage('')
    try {
      await createRegistration(propertyId, {
        registration_number: form.registration_number.trim(),
        registry_office: form.registry_office.trim() || undefined,
        comarca: form.comarca.trim() || undefined,
        consultation_date: form.consultation_date || undefined,
        holder: form.holder.trim() || undefined,
        observations: form.observations.trim() || undefined,
      })
      setFormOpen(false)
      setForm(initialForm)
      setSuccessMessage('Matrícula registrada com sucesso.')
      await loadRegistration()
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível registrar a matrícula.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Matrícula" description="Registros da matrícula do imóvel e seu histórico de consultas." className="dossier-section" actions={<Button onClick={openForm}><Plus size={16} /> Novo registro</Button>}>
      {successMessage && <Alert tone="success" title="Registro concluído" className="dossier-feedback">{successMessage}</Alert>}

      {formOpen && (
        <Card variant="elevated" padding="lg" className="dossier-form-card">
          <form className="dossier-form" onSubmit={handleSubmit} noValidate>
            <Input label="Número da matrícula" placeholder="Ex.: 12.345" value={form.registration_number} onChange={(event) => updateField('registration_number', event.target.value)} error={fieldError} required />
            <Input label="Cartório (opcional)" value={form.registry_office} onChange={(event) => updateField('registry_office', event.target.value)} />
            <Input label="Comarca (opcional)" value={form.comarca} onChange={(event) => updateField('comarca', event.target.value)} />
            <Input label="Data da consulta (opcional)" type="date" value={form.consultation_date} onChange={(event) => updateField('consultation_date', event.target.value)} />
            <Input label="Titular (opcional)" value={form.holder} onChange={(event) => updateField('holder', event.target.value)} />
            <Textarea label="Observações (opcional)" value={form.observations} onChange={(event) => updateField('observations', event.target.value)} className="dossier-form-full" />
            <div className="dossier-form-actions">
              {saveError && <Alert tone="danger">{saveError}</Alert>}
              <Button variant="ghost" type="button" onClick={() => setFormOpen(false)} disabled={saving}>Cancelar</Button>
              <Button type="submit" loading={saving}>Salvar matrícula</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingState label="Carregando matrícula…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadRegistration()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : !current ? (
        <Card padding="none"><EmptyState title="Nenhuma matrícula cadastrada" description="Cadastre um registro de matrícula para compor o dossiê do imóvel." icon={<FileSignature size={24} />} action={<Button onClick={openForm}><Plus size={16} /> Novo registro</Button>} /></Card>
      ) : (
        <>
          <Card padding="lg" className="dossier-current">
            <div className="dossier-current-head">
              <div>
                <p className="eyebrow">MATRÍCULA ATUAL</p>
                <h3>{current.registration_number || 'Sem número informado'}</h3>
              </div>
              {current.document_version_id && <Badge tone="info" size="sm">Vinculada a documento</Badge>}
            </div>
            <dl className="dossier-facts">
              <Fact label="Cartório" value={current.registry_office} />
              <Fact label="Comarca" value={current.comarca} />
              <Fact label="Consulta" value={formatDate(current.consultation_date)} />
              <Fact label="Titular" value={current.holder} />
              <Fact label="Observações" value={current.observations} />
            </dl>
          </Card>

          {history.length > 0 && (
            <div className="dossier-history">
              <p className="dossier-history-title">Histórico de registros</p>
              <div className="dossier-timeline">
                {history.slice().reverse().map((item) => (
                  <div key={item.id} className="dossier-timeline-item">
                    <span className="dossier-timeline-dot" />
                    <div>
                      <strong>{item.registration_number || 'Sem número'}</strong>
                      <span>{formatDate(item.consultation_date)} · {item.registry_office || 'Cartório não informado'}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
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
