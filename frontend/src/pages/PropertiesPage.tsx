import { useCallback, useEffect, useState } from 'react'
import { Building2, MapPin, Plus, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section } from '../components/ui'
import { listProperties, type Property } from '../services/properties'
import { PropertyWizard } from './PropertyWizard'

type PropertiesPageProps = {
  onOpenProperty?: (id: number) => void
}

export function PropertiesPage({ onOpenProperty }: PropertiesPageProps = {}) {
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [wizardOpen, setWizardOpen] = useState(false)

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

  const handleCreated = (id: number) => {
    setWizardOpen(false)
    if (onOpenProperty) {
      onOpenProperty(id)
    } else {
      void loadProperties()
    }
  }

  return (
    <Section className="properties-page">
      <div className="properties-toolbar">
        <div>
          <p className="properties-count">{properties.length} {properties.length === 1 ? 'imóvel cadastrado' : 'imóveis cadastrados'}</p>
          <p className="page-description">Acompanhe os imóveis que fazem parte do seu radar.</p>
        </div>
        {!wizardOpen && <Button onClick={() => setWizardOpen(true)}><Plus size={17} /> Novo imóvel</Button>}
      </div>

      {error && properties.length > 0 && <Alert tone="danger" title="Não foi possível carregar" className="properties-feedback" onDismiss={() => setError('')}>{error}</Alert>}

      {wizardOpen && (
        <PropertyWizard onCancel={() => setWizardOpen(false)} onCreated={handleCreated} />
      )}

      {!wizardOpen && (
        <Section title="Imóveis cadastrados" className="properties-list-section">
          {loading ? (
            <LoadingState label="Carregando imóveis…" />
          ) : error && properties.length === 0 ? (
            <Card padding="lg" className="properties-error">
              <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
              <Button variant="secondary" onClick={() => void loadProperties()}><RefreshCw size={16} /> Tentar novamente</Button>
            </Card>
          ) : properties.length === 0 ? (
            <Card padding="none"><EmptyState title="Nenhum imóvel cadastrado" description="Comece adicionando o primeiro imóvel ao seu radar." icon={<Building2 size={24} />} action={<Button onClick={() => setWizardOpen(true)}><Plus size={17} /> Novo imóvel</Button>} /></Card>
          ) : (
            <div className="property-grid">
              {properties.map((property) => <PropertyCard key={property.id} property={property} onOpen={onOpenProperty} />)}
            </div>
          )}
        </Section>
      )}
    </Section>
  )
}

function PropertyCard({ property, onOpen }: { property: Property; onOpen?: (id: number) => void }) {
  return (
    <Card className="property-card" padding="none">
      <button type="button" className="property-card-button" onClick={() => onOpen?.(property.id)}>
        <div className="property-card-head">
          <div className="property-card-icon"><Building2 size={20} /></div>
          <Badge tone={property.status === 'EM_ANALISE' ? 'warning' : 'neutral'} size="sm">{property.status.split('_').join(' ')}</Badge>
        </div>
        <h3>{property.title}</h3>
        <p className="property-address"><MapPin size={14} /> {property.address || 'Endereço não informado'}</p>
        <div className="property-card-meta">
          <span>{property.city} · {property.state}</span>
          <strong>{property.property_type}</strong>
        </div>
      </button>
    </Card>
  )
}
