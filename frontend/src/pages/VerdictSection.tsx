import { useCallback, useEffect, useState } from 'react'
import { BadgeCheck, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section } from '../components/ui'
import { getAssessment, type Verdict, type VerdictEvidence } from '../services/assessment'

const categoryLabels: Record<string, string> = {
  DOCUMENTAL: 'Documental',
  JURIDICO: 'Jurídico',
  FINANCEIRO: 'Financeiro',
  MERCADO: 'Mercado',
  CHECKLIST: 'Checklist',
}

function categoryLabel(category?: string | null) {
  if (!category) return null
  return categoryLabels[category] ?? category
}

type VerdictSectionProps = {
  propertyId: number
}

const overallTone: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  FAVORAVEL: 'success',
  ATENCAO: 'warning',
  DESFAVORAVEL: 'danger',
  INCONCLUSIVO: 'neutral',
  PENDENTE: 'neutral',
}

const overallLabels: Record<string, string> = {
  FAVORAVEL: 'Favorável',
  ATENCAO: 'Atenção',
  DESFAVORAVEL: 'Desfavorável',
  INCONCLUSIVO: 'Inconclusivo',
  PENDENTE: 'Pendente',
}

function overallLabel(overall?: string | null) {
  if (!overall) return 'Pendente'
  return overallLabels[overall] ?? overall
}

export function VerdictSection({ propertyId }: VerdictSectionProps) {
  const [verdict, setVerdict] = useState<Verdict | null>(null)
  const [evidences, setEvidences] = useState<VerdictEvidence[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadVerdict = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const assessment = await getAssessment(propertyId)
      setVerdict(assessment.verdict)
      setEvidences(assessment.evidences)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o veredito.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadVerdict() }, [loadVerdict])

  return (
    <Section title="Veredito" description="Veredito consolidado pelo motor determinístico do Radar Leilão." className="dossier-section">
      {loading ? (
        <LoadingState label="Carregando veredito…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadVerdict()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : !verdict ? (
        <Card padding="none"><EmptyState title="Veredito não disponível" description="Ainda não há um veredito consolidado para este imóvel." icon={<BadgeCheck size={24} />} /></Card>
      ) : (
        <>
          <Card variant="brand" padding="lg" className="verdict-hero">
            <div className="verdict-hero-info">
              <p className="eyebrow">VEREDITO CONSOLIDADO</p>
              <h3>{overallLabel(verdict.overall)}</h3>
              {verdict.summary && <p className="verdict-summary">{verdict.summary}</p>}
            </div>
            <Badge tone={overallTone[verdict.overall ?? 'PENDENTE'] ?? 'neutral'} size="md" className="verdict-badge">{overallLabel(verdict.overall)}</Badge>
          </Card>

          <div className="verdict-grid">
            {verdict.what_is_known && (
              <Card padding="lg" className="verdict-block">
                <p className="eyebrow">O QUE SE SABE</p>
                <p>{verdict.what_is_known}</p>
              </Card>
            )}
            {verdict.what_is_unknown && (
              <Card padding="lg" className="verdict-block">
                <p className="eyebrow">O QUE FALTA CONFIRMAR</p>
                <p>{verdict.what_is_unknown}</p>
              </Card>
            )}
          </div>

          {verdict.pending_items && verdict.pending_items.length > 0 && (
            <Card padding="lg" className="verdict-block">
              <p className="eyebrow">PENDÊNCIAS</p>
              <ul className="verdict-pending">
                {verdict.pending_items.map((pending, index) => <li key={index}>{pending}</li>)}
              </ul>
            </Card>
          )}

          <dl className="dossier-facts verdict-facts">
            {verdict.analysis_version != null && <Fact label="Versão da análise" value={String(verdict.analysis_version)} />}
            {verdict.risk_ids && verdict.risk_ids.length > 0 && <Fact label="Riscos vinculados" value={verdict.risk_ids.map((id) => `#${id}`).join(', ')} />}
          </dl>

          {(evidences.length > 0 || (verdict.evidence_ids && verdict.evidence_ids.length > 0)) && (
            <Card padding="lg" className="verdict-block">
              <p className="eyebrow">EVIDÊNCIAS VINCULADAS</p>
              {evidences.length > 0 ? (
                <ul className="verdict-evidences">
                  {evidences.map((evidence) => <EvidenceItem key={evidence.id} evidence={evidence} />)}
                </ul>
              ) : (
                // Fallback de rastreabilidade: se a visão legível não veio, mostra os IDs.
                <p className="verdict-evidence-ids">{verdict.evidence_ids?.map((id) => `#${id}`).join(', ')}</p>
              )}
            </Card>
          )}
        </>
      )}
    </Section>
  )
}

function EvidenceItem({ evidence }: { evidence: VerdictEvidence }) {
  const title = evidence.documento ?? (evidence.chunk_id != null ? `Trecho #${evidence.chunk_id}` : `Evidência #${evidence.id}`)
  const meta: string[] = []
  const category = categoryLabel(evidence.category)
  if (category) meta.push(category)
  if (evidence.version != null) meta.push(`versão ${evidence.version}`)
  if (evidence.page != null) meta.push(`Página ${evidence.page}`)
  if (evidence.section) meta.push(evidence.section)
  const description = evidence.fact ?? evidence.source_excerpt ?? evidence.interpretation ?? null
  return (
    <li className="verdict-evidence">
      <p className="verdict-evidence-title">📄 {title}</p>
      {meta.length > 0 && <p className="verdict-evidence-meta">{meta.join(' · ')}</p>}
      {description && <p className="verdict-evidence-desc">{description}</p>}
    </li>
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
