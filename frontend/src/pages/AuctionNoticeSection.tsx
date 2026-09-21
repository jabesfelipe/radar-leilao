import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Gavel, Plus, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section, Textarea } from '../components/ui'
import { createNotice, getNotice, type AuctionNotice } from '../services/registration'

type AuctionNoticeSectionProps = {
  propertyId: number
}

type NoticeForm = {
  identifier: string
  notice_date: string
  auction_stage: string
  appraisal_value: string
  minimum_value: string
  auction_date: string
  auctioneer: string
  observations: string
}

const initialForm: NoticeForm = {
  identifier: '',
  notice_date: '',
  auction_stage: '',
  appraisal_value: '',
  minimum_value: '',
  auction_date: '',
  auctioneer: '',
  observations: '',
}

function formatDate(value?: string | null) {
  if (!value) return 'Não informado'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR')
}

function formatMoney(value?: number | string | null) {
  if (value === undefined || value === null || value === '') return 'Não informado'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(numeric)
}

export function AuctionNoticeSection({ propertyId }: AuctionNoticeSectionProps) {
  const [current, setCurrent] = useState<AuctionNotice | null>(null)
  const [history, setHistory] = useState<AuctionNotice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<NoticeForm>(initialForm)
  const [fieldError, setFieldError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const loadNotice = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getNotice(propertyId)
      setCurrent(data.atual)
      setHistory(data.historico ?? [])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o edital.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadNotice() }, [loadNotice])

  const openForm = () => {
    setForm(initialForm)
    setFieldError('')
    setSaveError('')
    setSuccessMessage('')
    setFormOpen(true)
  }

  const updateField = (field: keyof NoticeForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    if (field === 'identifier') setFieldError('')
    setSaveError('')
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!form.identifier.trim()) {
      setFieldError('Informe o identificador do edital.')
      return
    }
    setSaving(true)
    setSaveError('')
    setSuccessMessage('')
    try {
      await createNotice(propertyId, {
        identifier: form.identifier.trim(),
        notice_date: form.notice_date || undefined,
        auction_stage: form.auction_stage.trim() || undefined,
        appraisal_value: form.appraisal_value.trim() ? Number(form.appraisal_value) : undefined,
        minimum_value: form.minimum_value.trim() ? Number(form.minimum_value) : undefined,
        auction_date: form.auction_date || undefined,
        auctioneer: form.auctioneer.trim() || undefined,
        observations: form.observations.trim() || undefined,
      })
      setFormOpen(false)
      setForm(initialForm)
      setSuccessMessage('Edital registrado com sucesso.')
      await loadNotice()
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível registrar o edital.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Edital" description="Editais do leilão vinculados ao imóvel e seu histórico." className="dossier-section" actions={<Button onClick={openForm}><Plus size={16} /> Novo edital</Button>}>
      {successMessage && <Alert tone="success" title="Registro concluído" className="dossier-feedback">{successMessage}</Alert>}

      {formOpen && (
        <Card variant="elevated" padding="lg" className="dossier-form-card">
          <form className="dossier-form" onSubmit={handleSubmit} noValidate>
            <Input label="Identificador" placeholder="Ex.: Edital 001/2026" value={form.identifier} onChange={(event) => updateField('identifier', event.target.value)} error={fieldError} required />
            <Input label="Data do edital (opcional)" type="date" value={form.notice_date} onChange={(event) => updateField('notice_date', event.target.value)} />
            <Input label="Praça/Fase (opcional)" placeholder="Ex.: 2º leilão" value={form.auction_stage} onChange={(event) => updateField('auction_stage', event.target.value)} />
            <Input label="Valor de avaliação (opcional)" type="number" step="0.01" value={form.appraisal_value} onChange={(event) => updateField('appraisal_value', event.target.value)} />
            <Input label="Valor mínimo (opcional)" type="number" step="0.01" value={form.minimum_value} onChange={(event) => updateField('minimum_value', event.target.value)} />
            <Input label="Data do leilão (opcional)" type="date" value={form.auction_date} onChange={(event) => updateField('auction_date', event.target.value)} />
            <Input label="Leiloeiro (opcional)" value={form.auctioneer} onChange={(event) => updateField('auctioneer', event.target.value)} />
            <Textarea label="Observações (opcional)" value={form.observations} onChange={(event) => updateField('observations', event.target.value)} className="dossier-form-full" />
            <div className="dossier-form-actions">
              {saveError && <Alert tone="danger">{saveError}</Alert>}
              <Button variant="ghost" type="button" onClick={() => setFormOpen(false)} disabled={saving}>Cancelar</Button>
              <Button type="submit" loading={saving}>Salvar edital</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingState label="Carregando edital…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadNotice()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : !current ? (
        <Card padding="none"><EmptyState title="Nenhum edital cadastrado" description="Cadastre um edital para compor o dossiê do leilão." icon={<Gavel size={24} />} action={<Button onClick={openForm}><Plus size={16} /> Novo edital</Button>} /></Card>
      ) : (
        <>
          <Card padding="lg" className="dossier-current">
            <div className="dossier-current-head">
              <div>
                <p className="eyebrow">EDITAL ATUAL</p>
                <h3>{current.identifier || 'Sem identificador'}</h3>
              </div>
              {current.document_version_id && <Badge tone="info" size="sm">Vinculado a documento</Badge>}
            </div>
            <dl className="dossier-facts">
              <Fact label="Data do edital" value={formatDate(current.notice_date)} />
              <Fact label="Praça/Fase" value={current.auction_stage} />
              <Fact label="Avaliação" value={formatMoney(current.appraisal_value)} />
              <Fact label="Valor mínimo" value={formatMoney(current.minimum_value)} />
              <Fact label="Data do leilão" value={formatDate(current.auction_date)} />
              <Fact label="Leiloeiro" value={current.auctioneer} />
              <Fact label="Observações" value={current.observations} />
            </dl>
          </Card>

          {history.length > 0 && (
            <div className="dossier-history">
              <p className="dossier-history-title">Histórico de editais</p>
              <div className="dossier-timeline">
                {history.slice().reverse().map((item) => (
                  <div key={item.id} className="dossier-timeline-item">
                    <span className="dossier-timeline-dot" />
                    <div>
                      <strong>{item.identifier || 'Sem identificador'}</strong>
                      <span>{formatDate(item.notice_date)} · {item.auction_stage || 'Fase não informada'}</span>
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
