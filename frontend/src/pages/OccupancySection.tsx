import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Home, Plus, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section, Select } from '../components/ui'
import { createOccupancy, formatMoney, getOccupancy, type Occupancy, type OccupancyStatus } from '../services/market'

type OccupancySectionProps = {
  propertyId: number
}

type OccupancyForm = {
  status: OccupancyStatus
  occupant_profile: string
  estimated_cost: string
  estimated_months: string
}

const statusOptions: OccupancyStatus[] = ['OCUPADO', 'DESOCUPADO', 'DESCONHECIDO']

const initialForm: OccupancyForm = { status: 'DESCONHECIDO', occupant_profile: '', estimated_cost: '', estimated_months: '' }

const statusTone: Record<OccupancyStatus, 'warning' | 'success' | 'neutral'> = {
  OCUPADO: 'warning',
  DESOCUPADO: 'success',
  DESCONHECIDO: 'neutral',
}

export function OccupancySection({ propertyId }: OccupancySectionProps) {
  const [occupancy, setOccupancy] = useState<Occupancy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<OccupancyForm>(initialForm)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const loadOccupancy = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getOccupancy(propertyId)
      setOccupancy(data.situacao_atual)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar a ocupação.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadOccupancy() }, [loadOccupancy])

  const openForm = () => {
    setForm(initialForm)
    setSaveError('')
    setSuccessMessage('')
    setFormOpen(true)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setSaveError('')
    setSuccessMessage('')
    try {
      await createOccupancy(propertyId, {
        status: form.status,
        occupant_profile: form.occupant_profile.trim() || undefined,
        estimated_cost: form.estimated_cost.trim() ? Number(form.estimated_cost) : undefined,
        estimated_months: form.estimated_months.trim() ? Number(form.estimated_months) : undefined,
      })
      setFormOpen(false)
      setForm(initialForm)
      setSuccessMessage('Ocupação registrada com sucesso.')
      await loadOccupancy()
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível registrar a ocupação.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Ocupação" description="Situação de ocupação registrada para o imóvel." className="dossier-section" actions={<Button onClick={openForm}><Plus size={16} /> Registrar ocupação</Button>}>
      {successMessage && <Alert tone="success" title="Registro concluído" className="dossier-feedback">{successMessage}</Alert>}

      {formOpen && (
        <Card variant="elevated" padding="lg" className="dossier-form-card">
          <form className="dossier-form" onSubmit={handleSubmit} noValidate>
            <Select label="Status" value={form.status} onChange={(event) => setForm((c) => ({ ...c, status: event.target.value as OccupancyStatus }))}>
              {statusOptions.map((status) => <option key={status} value={status}>{status}</option>)}
            </Select>
            <Input label="Perfil do ocupante (opcional)" value={form.occupant_profile} onChange={(event) => setForm((c) => ({ ...c, occupant_profile: event.target.value }))} />
            <Input label="Custo estimado (opcional)" type="number" step="0.01" value={form.estimated_cost} onChange={(event) => setForm((c) => ({ ...c, estimated_cost: event.target.value }))} />
            <Input label="Meses estimados (opcional)" type="number" min="0" value={form.estimated_months} onChange={(event) => setForm((c) => ({ ...c, estimated_months: event.target.value }))} />
            <div className="dossier-form-actions">
              {saveError && <Alert tone="danger">{saveError}</Alert>}
              <Button variant="ghost" type="button" onClick={() => setFormOpen(false)} disabled={saving}>Cancelar</Button>
              <Button type="submit" loading={saving}>Salvar ocupação</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingState label="Carregando ocupação…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadOccupancy()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : !occupancy ? (
        <Card padding="none"><EmptyState title="Nenhuma ocupação registrada" description="Registre a situação de ocupação para compor o dossiê." icon={<Home size={24} />} action={<Button onClick={openForm}><Plus size={16} /> Registrar ocupação</Button>} /></Card>
      ) : (
        <Card padding="lg" className="dossier-current">
          <div className="dossier-current-head">
            <div>
              <p className="eyebrow">SITUAÇÃO ATUAL</p>
              <h3>{occupancy.status}</h3>
            </div>
            <Badge tone={statusTone[occupancy.status] ?? 'neutral'} size="md">{occupancy.status}</Badge>
          </div>
          <dl className="dossier-facts">
            <Fact label="Perfil do ocupante" value={occupancy.occupant_profile} />
            <Fact label="Custo estimado" value={occupancy.estimated_cost == null ? 'Não informado' : formatMoney(occupancy.estimated_cost)} />
            <Fact label="Meses estimados" value={occupancy.estimated_months == null ? 'Não informado' : String(occupancy.estimated_months)} />
            {occupancy.evidence_id != null && <Fact label="Evidência" value={`#${occupancy.evidence_id}`} />}
          </dl>
        </Card>
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
