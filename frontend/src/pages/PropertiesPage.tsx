import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Building2, MapPin, Plus, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import { createProperty, listProperties, type Property, type PropertyCreate } from '../services/properties'

type PropertyForm = PropertyCreate

type FieldErrors = Partial<Record<keyof PropertyForm, string>>

const initialForm: PropertyForm = {
  title: '',
  address: '',
  city: '',
  state: '',
  property_type: 'Apartamento',
}

function validate(form: PropertyForm): FieldErrors {
  const errors: FieldErrors = {}
  if (form.title.trim().length < 2) errors.title = 'Informe um título com pelo menos 2 caracteres.'
  if (!form.address.trim()) errors.address = 'Informe o endereço.'
  if (!form.city.trim()) errors.city = 'Informe a cidade.'
  if (form.state.trim().length !== 2) errors.state = 'Informe a UF com 2 caracteres.'
  if (!form.property_type.trim()) errors.property_type = 'Selecione o tipo do imóvel.'
  return errors
}

export function PropertiesPage() {
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<PropertyForm>(initialForm)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const loadProperties = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setProperties(await listProperties())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os imóveis.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadProperties() }, [loadProperties])

  const openForm = () => {
    setForm(initialForm)
    setFieldErrors({})
    setSaveError('')
    setSuccessMessage('')
    setFormOpen(true)
  }

  const closeForm = () => {
    if (!saving) setFormOpen(false)
  }

  const updateField = (field: keyof PropertyForm, value: string) => {
    setForm((current) => ({ ...current, [field]: field === 'state' ? value.toUpperCase() : value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    setSaveError('')
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const errors = validate(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSaving(true)
    setSaveError('')
    setSuccessMessage('')
    try {
      const created = await createProperty({
        title: form.title.trim(),
        address: form.address.trim(),
        city: form.city.trim(),
        state: form.state.trim().toUpperCase(),
        property_type: form.property_type,
      })
      setProperties((current) => [created, ...current])
      setFormOpen(false)
      setForm(initialForm)
      setSuccessMessage('Imóvel cadastrado com sucesso.')
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível salvar o imóvel.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section className="properties-page">
      <div className="properties-toolbar">
        <div>
          <p className="properties-count">{properties.length} {properties.length === 1 ? 'imóvel cadastrado' : 'imóveis cadastrados'}</p>
          <p className="page-description">Acompanhe os imóveis que fazem parte do seu radar.</p>
        </div>
        <Button onClick={openForm}><Plus size={17} /> Novo imóvel</Button>
      </div>

      {successMessage && <Alert tone="success" title="Cadastro concluído" className="properties-feedback">{successMessage}</Alert>}
      {error && <Alert tone="danger" title="Não foi possível carregar" className="properties-feedback" onDismiss={() => setError('')}>{error}</Alert>}

      {formOpen && (
        <Card variant="elevated" padding="lg" className="property-form-card">
          <Section title="Novo imóvel" description="Preencha apenas as informações básicas do imóvel." actions={<Button variant="ghost" onClick={closeForm} disabled={saving}>Cancelar</Button>}>
            <form className="property-form" onSubmit={handleSubmit} noValidate>
              <Input label="Título ou identificação" placeholder="Ex.: Apartamento Centro" value={form.title} onChange={(event) => updateField('title', event.target.value)} error={fieldErrors.title} required />
              <Input label="Endereço" placeholder="Rua, número e complemento" value={form.address} onChange={(event) => updateField('address', event.target.value)} error={fieldErrors.address} required />
              <Input label="Cidade" placeholder="Ex.: São Paulo" value={form.city} onChange={(event) => updateField('city', event.target.value)} error={fieldErrors.city} required />
              <Input label="Estado (UF)" placeholder="SP" maxLength={2} value={form.state} onChange={(event) => updateField('state', event.target.value)} error={fieldErrors.state} required />
              <Input label="Tipo do imóvel" placeholder="Ex.: Apartamento" value={form.property_type} onChange={(event) => updateField('property_type', event.target.value)} error={fieldErrors.property_type} required />
              <div className="property-form-actions">
                {saveError && <Alert tone="danger">{saveError}</Alert>}
                <Button type="submit" loading={saving}>Salvar imóvel</Button>
              </div>
            </form>
          </Section>
        </Card>
      )}

      <Section title="Imóveis cadastrados" className="properties-list-section">
        {loading ? <LoadingState label="Carregando imóveis…" /> : properties.length === 0 ? (
          <Card padding="none"><EmptyState title="Nenhum imóvel cadastrado" description="Comece adicionando o primeiro imóvel ao seu radar." icon={<Building2 size={24} />} action={<Button onClick={openForm}><Plus size={17} /> Novo imóvel</Button>} /></Card>
        ) : (
          <div className="property-grid">
            {properties.map((property) => <PropertyCard key={property.id} property={property} />)}
          </div>
        )}
      </Section>
      {!loading && error && properties.length === 0 && <Button variant="secondary" onClick={() => void loadProperties()}><RefreshCw size={16} /> Tentar novamente</Button>}
    </Section>
  )
}

function PropertyCard({ property }: { property: Property }) {
  return (
    <Card className="property-card" padding="md">
      <div className="property-card-head">
        <div className="property-card-icon"><Building2 size={20} /></div>
        <Badge tone={property.status === 'EM_ANALISE' ? 'warning' : 'neutral'} size="sm">{property.status.split('_').join(' ')}</Badge>
      </div>
      <h3>{property.title}</h3>
      <p className="property-address"><MapPin size={14} /> {property.address}</p>
      <div className="property-card-meta">
        <span>{property.city} · {property.state}</span>
        <strong>{property.property_type}</strong>
      </div>
    </Card>
  )
}
