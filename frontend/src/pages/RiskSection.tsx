import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, ShieldAlert, ShieldCheck } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section } from '../components/ui'
import { getAssessment, type Risk } from '../services/assessment'

type RiskSectionProps = {
  propertyId: number
}

const severityTone: Record<string, 'neutral' | 'warning' | 'danger' | 'info'> = {
  BAIXA: 'info',
  MEDIA: 'warning',
  ALTA: 'danger',
  CRITICA: 'danger',
}

const severityLabels: Record<string, string> = {
  BAIXA: 'Baixa',
  MEDIA: 'Média',
  ALTA: 'Alta',
  CRITICA: 'Crítica',
}

const confidenceLabels: Record<string, string> = {
  BAIXA: 'Baixa',
  MEDIA: 'Média',
  ALTA: 'Alta',
}

export function RiskSection({ propertyId }: RiskSectionProps) {
  const [risks, setRisks] = useState<Risk[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadRisks = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const assessment = await getAssessment(propertyId)
      setRisks(assessment.risks)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os riscos.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadRisks() }, [loadRisks])

  return (
    <Section title="Riscos" description="Riscos identificados pelo motor determinístico do Radar Leilão." className="dossier-section">
      {loading ? (
        <LoadingState label="Carregando riscos…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadRisks()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : risks.length === 0 ? (
        <Card padding="none"><EmptyState title="Nenhum risco identificado" description="Não há riscos registrados para este imóvel nesta análise." icon={<ShieldCheck size={24} />} /></Card>
      ) : (
        <div className="risk-list">
          {risks.map((risk) => (
            <Card key={risk.id} padding="lg" className="risk-card">
              <div className="risk-card-head">
                <div className="risk-card-title">
                  <div className="risk-card-icon"><ShieldAlert size={19} /></div>
                  <h3>{risk.category || 'Risco'}</h3>
                </div>
                {risk.severity && <Badge tone={severityTone[risk.severity] ?? 'neutral'} size="sm">{severityLabels[risk.severity] ?? risk.severity}</Badge>}
              </div>
              {risk.description && <p className="risk-description">{risk.description}</p>}
              <dl className="dossier-facts">
                {risk.impact && <Fact label="Impacto" value={risk.impact} />}
                {risk.confidence && <Fact label="Confiança" value={confidenceLabels[risk.confidence] ?? risk.confidence} />}
                {risk.status && <Fact label="Status" value={risk.status.split('_').join(' ')} />}
                {risk.origin && <Fact label="Origem" value={risk.origin} />}
                {risk.analysis_version != null && <Fact label="Versão da análise" value={String(risk.analysis_version)} />}
                {risk.evidence_id != null && <Fact label="Evidência" value={`#${risk.evidence_id}`} />}
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
