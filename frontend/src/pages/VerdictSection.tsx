import { useCallback, useEffect, useState } from 'react'
import { BadgeCheck, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section } from '../components/ui'
import { getAssessment, verdictDecision, type ComparisonSide, type DocumentComparison, type Verdict, type VerdictEvidence, type VerdictGround } from '../services/assessment'

// Natureza de cada fundamento: o investidor precisa distinguir risco jurídico, pendência documental
// e inviabilidade financeira (e saber quando a leitura automática simplesmente não rodou).
const groundGroups: { tipo: string; titulo: string; tone: 'danger' | 'warning' | 'info' | 'success' | 'neutral' }[] = [
  { tipo: 'INVIABILIDADE_FINANCEIRA', titulo: 'Inviabilidade financeira', tone: 'danger' },
  { tipo: 'RISCO_JURIDICO', titulo: 'Risco jurídico', tone: 'danger' },
  { tipo: 'RISCO_OPERACIONAL', titulo: 'Risco operacional', tone: 'warning' },
  { tipo: 'VIABILIDADE_FINANCEIRA', titulo: 'Viabilidade financeira', tone: 'success' },
  { tipo: 'PENDENCIA_FINANCEIRA', titulo: 'Dados financeiros pendentes', tone: 'warning' },
  { tipo: 'PENDENCIA_DOCUMENTAL', titulo: 'Pendências documentais', tone: 'info' },
  { tipo: 'ANALISE_AUTOMATICA_INDISPONIVEL', titulo: 'Leitura automática dos documentos', tone: 'neutral' },
]

const recommendationTone: Record<string, 'danger' | 'warning' | 'success' | 'info'> = {
  NAO_ARREMATAR: 'danger',
  ARREMATAR_SOMENTE_APOS_RESOLVER_RISCOS: 'warning',
  ARREMATAR_ATE_PRECO_MAXIMO: 'success',
  COMPLETAR_ANALISE: 'info',
}

const recommendationTitle: Record<string, string> = {
  NAO_ARREMATAR: 'Não arrematar por este lance',
  ARREMATAR_SOMENTE_APOS_RESOLVER_RISCOS: 'Arrematar só após resolver os riscos',
  ARREMATAR_ATE_PRECO_MAXIMO: 'Arrematar até o preço máximo',
  COMPLETAR_ANALISE: 'Análise incompleta',
}

function formatBRL(value?: number | null) {
  if (value == null || Number.isNaN(Number(value))) return null
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

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
  const [comparisons, setComparisons] = useState<DocumentComparison[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadVerdict = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const assessment = await getAssessment(propertyId)
      setVerdict(assessment.verdict)
      setEvidences(assessment.evidences)
      setComparisons(assessment.comparisons ?? [])
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

          <RecommendationBlock verdict={verdict} />

          <ComparisonBlock comparisons={comparisons} />

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

const comparisonInfo: Record<string, { label: string; tone: 'danger' | 'warning' | 'info' | 'success' | 'neutral' }> = {
  DIVERGENCIA: { label: 'Divergência', tone: 'warning' },
  CONFERE: { label: 'Confere', tone: 'success' },
  NAO_COMPARAVEL: { label: 'Não comparável', tone: 'neutral' },
}

function ComparisonSideText({ side }: { side?: ComparisonSide | null }) {
  if (!side) return <span className="verdict-evidence-meta">Não localizado</span>
  return (
    <span>
      <strong>{side.valor_texto ?? side.valor}</strong>
      {side.trecho && <span className="verdict-evidence-meta"> — “{side.trecho}” ({side.documento}{side.pagina != null ? `, pág. ${side.pagina}` : ''})</span>}
    </span>
  )
}

// Confronto matrícula × edital: mostra as duas fontes; divergência é fato a validar, não irregularidade presumida.
function ComparisonBlock({ comparisons }: { comparisons: DocumentComparison[] }) {
  if (comparisons.length === 0) return null
  const divergences = comparisons.filter((row) => row.resultado === 'DIVERGENCIA').length
  return (
    <Card padding="lg" className="verdict-block">
      <p className="eyebrow">CONFRONTO DOCUMENTAL (MATRÍCULA × EDITAL)</p>
      {divergences > 0 && <Alert tone="warning" title={divergences === 1 ? '1 divergência entre documentos' : `${divergences} divergências entre documentos`}>Validar antes de decidir.</Alert>}
      <ul className="verdict-evidences" aria-label="Confronto documental">
        {comparisons.map((row) => {
          const info = comparisonInfo[row.resultado] ?? { label: row.resultado, tone: 'neutral' as const }
          return (
            <li key={row.informacao} className="verdict-evidence">
              <p className="verdict-evidence-title">{row.informacao} <Badge tone={info.tone} size="sm">{info.label}</Badge></p>
              <p className="verdict-evidence-desc">Matrícula: <ComparisonSideText side={row.matricula} /></p>
              <p className="verdict-evidence-desc">Edital: <ComparisonSideText side={row.edital} /></p>
              {row.observacao && <p className="verdict-evidence-meta">{row.observacao}</p>}
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

function RecommendationBlock({ verdict }: { verdict: Verdict }) {
  const decision = verdictDecision(verdict)
  const recommendation = decision?.recomendacao
  if (!recommendation) return null
  const tone = recommendationTone[recommendation.codigo] ?? 'info'
  const maxBid = formatBRL(recommendation.lance_maximo)
  const intendedBid = formatBRL(recommendation.lance_pretendido)
  const grounds = decision?.fundamentos ?? []
  return (
    <Card padding="lg" className="verdict-block verdict-recommendation">
      <p className="eyebrow">RECOMENDAÇÃO AO INVESTIDOR</p>
      <Alert tone={tone} title={recommendationTitle[recommendation.codigo] ?? recommendation.codigo}>{recommendation.texto}</Alert>
      {(intendedBid || maxBid) && (
        <dl className="dossier-facts verdict-facts">
          {intendedBid && <Fact label="Lance pretendido" value={intendedBid} />}
          {maxBid && <Fact label={recommendation.lance_maximo_definitivo ? 'Preço máximo (meta)' : 'Preço máximo (provisório)'} value={maxBid} />}
        </dl>
      )}
      {grounds.length > 0 && (
        <div className="verdict-grounds">
          {groundGroups.map((group) => {
            const items = grounds.filter((ground: VerdictGround) => ground.tipo === group.tipo)
            if (items.length === 0) return null
            return (
              <div key={group.tipo} className="verdict-ground-group">
                <p className="verdict-ground-title"><Badge tone={group.tone} size="sm">{group.titulo}</Badge> <span className="verdict-ground-count">{items.length}</span></p>
                <ul className="verdict-pending">
                  {items.slice(0, 8).map((ground, index) => <li key={index}>{ground.descricao}</li>)}
                  {items.length > 8 && <li>… e mais {items.length - 8}</li>}
                </ul>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}

// Origem da informação (v1.0.4): o investidor distingue fato lido no documento, dado cadastrado, cálculo e
// inferência da IA. Registros anteriores (sem origem) continuam exibidos como antes.
const originInfo: Record<string, { label: string; tone: 'danger' | 'warning' | 'info' | 'success' | 'neutral'; icon: string; note?: string }> = {
  DOCUMENTO: { label: 'Fato do documento', tone: 'success', icon: '📄' },
  CADASTRO: { label: 'Informação cadastrada', tone: 'info', icon: '🗂️', note: 'Informação cadastrada no Radar — não foi lida em documento.' },
  CALCULO: { label: 'Cálculo do Radar', tone: 'info', icon: '🧮', note: 'Resultado do cálculo determinístico — não é trecho de documento.' },
  PESQUISA_JUDICIAL: { label: 'Pesquisa judicial', tone: 'info', icon: '⚖️' },
  REGRA_DETERMINISTICA: { label: 'Regra determinística', tone: 'info', icon: '🧮' },
  INFERENCIA_IA: { label: 'Inferência da IA', tone: 'warning', icon: '💡', note: 'Inferência da IA — não comprovada por documento; validar antes de decidir.' },
}

const strengthInfo: Record<string, { label: string; tone: 'danger' | 'warning' | 'info' | 'success' | 'neutral' }> = {
  FORTE: { label: 'Evidência forte', tone: 'success' },
  MODERADA: { label: 'Evidência moderada', tone: 'info' },
  FRACA: { label: 'Citação fraca — não comprova', tone: 'warning' },
  INVALIDA: { label: 'Citação inválida — descartada', tone: 'danger' },
}

function EvidenceItem({ evidence }: { evidence: VerdictEvidence }) {
  const origin = evidence.origin ? originInfo[evidence.origin] : undefined
  const strength = evidence.strength ? strengthInfo[evidence.strength] : undefined
  const fallbackTitle = origin && evidence.origin !== 'DOCUMENTO' ? origin.label : `Evidência #${evidence.id}`
  const title = evidence.documento ?? (evidence.chunk_id != null ? `Trecho #${evidence.chunk_id}` : fallbackTitle)
  const meta: string[] = []
  const category = categoryLabel(evidence.category)
  if (category) meta.push(category)
  if (evidence.version != null) meta.push(`versão ${evidence.version}`)
  meta.push(evidence.page != null ? `Página ${evidence.page}` : 'Página não informada')
  meta.push(evidence.section ? `Seção ${evidence.section}` : 'Seção não informada')
  const statement = evidence.fact ?? evidence.interpretation ?? null
  const excerpt = evidence.source_excerpt ?? null
  return (
    <li className="verdict-evidence">
      <p className="verdict-evidence-title">{origin?.icon ?? '📄'} {title}</p>
      {(origin || strength) && (
        <p className="verdict-evidence-source" aria-label="Origem da informação">
          {origin && <Badge tone={origin.tone} size="sm">{origin.label}</Badge>}
          {strength && <Badge tone={strength.tone} size="sm">{strength.label}</Badge>}
        </p>
      )}
      <p className="verdict-evidence-meta">{meta.join(' · ')}</p>
      {statement && <p className="verdict-evidence-desc">{statement}</p>}
      {excerpt && statement !== excerpt ? (
        <blockquote className="verdict-evidence-excerpt" aria-label="Trecho literal do documento">“{excerpt}”</blockquote>
      ) : !excerpt ? (
        <p className="verdict-evidence-meta">{origin?.note ?? 'Sem trecho de documento vinculado.'}</p>
      ) : null}
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
