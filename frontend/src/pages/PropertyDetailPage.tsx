import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Building2, MapPin, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, LoadingState, Section } from '../components/ui'
import { getProperty, type Property } from '../services/properties'
import { DocumentsSection } from './DocumentsSection'
import { RegistrationSection } from './RegistrationSection'
import { AuctionNoticeSection } from './AuctionNoticeSection'

type PropertyDetailPageProps = {
  propertyId: number
  onBack: () => void
}

const detailSections = [
  { id: 'visao-geral', label: 'Visão geral' },
  { id: 'leilao', label: 'Leilão' },
  { id: 'documentos', label: 'Documentos' },
  { id: 'matricula', label: 'Matrícula' },
  { id: 'edital', label: 'Edital' },
  { id: 'juridico', label: 'Processos Jurídicos' },
  { id: 'financeiro', label: 'Financeiro' },
  { id: 'mercado', label: 'Mercado' },
  { id: 'ocupacao', label: 'Ocupação' },
  { id: 'checklist', label: 'Checklist' },
  { id: 'riscos', label: 'Riscos' },
  { id: 'veredito', label: 'Veredito' },
  { id: 'historico', label: 'Histórico' },
]

const initialSection = detailSections[0].id

function formatArea(value: Property['area_m2']) {
  if (value === undefined || value === null || value === '') return 'Não informado'
  const numeric = Number(value)
  return Number.isNaN(numeric) ? String(value) : `${numeric} m²`
}

export function PropertyDetailPage({ propertyId, onBack }: PropertyDetailPageProps) {
  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeSection, setActiveSection] = useState(initialSection)

  const loadProperty = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setProperty(await getProperty(propertyId))
    } catch (cause) {
      setProperty(null)
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o imóvel.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadProperty() }, [loadProperty])

  return (
    <Section className="property-detail">
      <Button variant="ghost" className="detail-back" onClick={onBack}><ArrowLeft size={17} /> Voltar para imóveis</Button>

      {loading ? (
        <LoadingState label="Carregando imóvel…" />
      ) : error || !property ? (
        <Card padding="lg" className="detail-error">
          <Alert tone="danger" title="Não foi possível abrir o imóvel">{error || 'Imóvel não encontrado.'}</Alert>
          <Button variant="secondary" onClick={() => void loadProperty()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : (
        <>
          <Card variant="brand" padding="lg" className="detail-hero">
            <div className="detail-hero-icon"><Building2 size={26} /></div>
            <div className="detail-hero-info">
              <p className="eyebrow">DOSSIÊ DO IMÓVEL</p>
              <h2>{property.title}</h2>
              <p className="detail-address"><MapPin size={15} /> {property.address}</p>
              <p className="detail-location">{property.city} · {property.state}</p>
            </div>
            <Badge tone={property.status === 'EM_ANALISE' ? 'warning' : 'neutral'} size="md" className="detail-status">{property.status.split('_').join(' ')}</Badge>
          </Card>

          <nav className="detail-nav" aria-label="Seções do imóvel">
            {detailSections.map((section) => (
              <button
                key={section.id}
                type="button"
                className={`detail-nav-item ${activeSection === section.id ? 'detail-nav-item-active' : ''}`}
                aria-current={activeSection === section.id ? 'page' : undefined}
                onClick={() => setActiveSection(section.id)}
              >
                {section.label}
              </button>
            ))}
          </nav>

          {activeSection === 'visao-geral' ? (
            <Section title="Visão geral" description="Informações básicas cadastradas para este imóvel." className="detail-section">
              <div className="detail-facts">
                <DetailFact label="Título" value={property.title} />
                <DetailFact label="Endereço" value={property.address} />
                <DetailFact label="Cidade" value={property.city} />
                <DetailFact label="Estado" value={property.state} />
                <DetailFact label="Tipo do imóvel" value={property.property_type} />
                <DetailFact label="Área" value={formatArea(property.area_m2)} />
                <DetailFact label="Quartos" value={property.bedrooms === undefined ? 'Não informado' : String(property.bedrooms)} />
                <DetailFact label="Status" value={property.status.split('_').join(' ')} />
              </div>
            </Section>
          ) : activeSection === 'documentos' ? (
            <DocumentsSection propertyId={property.id} />
          ) : activeSection === 'matricula' ? (
            <RegistrationSection propertyId={property.id} />
          ) : activeSection === 'edital' ? (
            <AuctionNoticeSection propertyId={property.id} />
          ) : (
            <Card padding="lg" className="detail-placeholder">
              <p className="eyebrow">MÓDULO EM PREPARAÇÃO</p>
              <h3>{detailSections.find((section) => section.id === activeSection)?.label}</h3>
              <p>Esta seção faz parte da estrutura do dossiê e receberá informações de análise em tarefas futuras.</p>
            </Card>
          )}
        </>
      )}
    </Section>
  )
}

function DetailFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-fact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
