import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, ShieldAlert, ShieldCheck } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section } from '../components/ui'
import { getConsolidatedRisks, type ConsolidatedRisk, type ConsolidatedRisks } from '../services/investment'

type RiskSectionProps = {
  propertyId: number
}

const situationTone: Record<string, 'neutral' | 'warning' | 'danger' | 'info' | 'success'> = {
  CONFIRMADO: 'danger',
  POSSIVEL: 'warning',
  PENDENTE_CONFIRMACAO: 'info',
  RESOLVIDO: 'success',
  NAO_IDENTIFICADO: 'neutral',
}

const impactLabels: Record<string, string> = { financeiro: 'Financeiro', prazo: 'Prazo', operacional: 'Operacional', 'jurídico': 'Jurídico' }

/** Riscos em linguagem simples (v1.0.14): um por assunto, no estado mais recente, agrupados por categoria, com o que fazer. */
export function RiskSection({ propertyId }: RiskSectionProps) {
  const [data, setData] = useState<ConsolidatedRisks | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadRisks = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await getConsolidatedRisks(propertyId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os riscos.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadRisks() }, [loadRisks])

  const items = data?.itens ?? []
  const open = items.filter((i) => i.situacao !== 'RESOLVIDO' && i.situacao !== 'NAO_IDENTIFICADO')
  const closed = items.filter((i) => i.situacao === 'RESOLVIDO' || i.situacao === 'NAO_IDENTIFICADO')
  const categories = Array.from(new Set(open.map((i) => i.categoria)))

  return (
    <Section title="Riscos" description="O que pode dar errado nesta compra, em linguagem simples, e o que fazer em cada caso." className="dossier-section">
      {loading ? (
        <LoadingState label="Carregando riscos…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadRisks()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : open.length === 0 && closed.length === 0 ? (
        <Card padding="none"><EmptyState title="Nenhum risco identificado" description="A análise não encontrou riscos nem pendências essenciais para este imóvel." icon={<ShieldCheck size={24} />} /></Card>
      ) : (
        <>
          {open.length === 0 ? <Alert tone="success">Nenhum risco ativo nem pendência essencial no momento.</Alert> : null}
          {categories.map((category) => (
            <div key={category} className="risk-list" aria-label={`Riscos: ${category}`}>
              <p className="dossier-history-title">{category}</p>
              {open.filter((i) => i.categoria === category).map((risk) => <RiskCard key={risk.chave} risk={risk} />)}
            </div>
          ))}
          {closed.length > 0 ? (
            <details className="registry-titularity">
              <summary>Verificados sem risco ou já resolvidos ({closed.length})</summary>
              <ul className="market-intel-reasons">
                {closed.map((r) => <li key={r.chave}><Badge tone={situationTone[r.situacao] ?? 'neutral'} size="sm">{r.situacao_label}</Badge> {r.titulo} <small className="market-obs">({r.categoria})</small></li>)}
              </ul>
            </details>
          ) : null}
          {data?.aviso ? <p className="market-obs">{data.aviso}</p> : null}
        </>
      )}
    </Section>
  )
}

function RiskCard({ risk }: { risk: ConsolidatedRisk }) {
  return (
    <Card padding="lg" className="risk-card">
      <div className="risk-card-head">
        <div className="risk-card-title">
          <div className="risk-card-icon"><ShieldAlert size={19} /></div>
          <h3>{risk.titulo}</h3>
        </div>
        <Badge tone={situationTone[risk.situacao] ?? 'neutral'} size="sm">{risk.situacao_label}</Badge>
      </div>
      <p className="risk-description">{risk.o_que_significa}</p>
      {risk.detalhe ? <p className="market-obs">{risk.detalhe}</p> : null}
      <dl className="dossier-facts">
        <Fact label="Impacto" value={risk.impactos.map((i) => impactLabels[i] ?? i).join(', ')} />
        {risk.gravidade_label ? <Fact label="Gravidade" value={risk.gravidade_label} /> : null}
        <Fact label="Estimativa" value={risk.estimativa.texto ?? 'Sem estimativa de valor.'} />
        {risk.evidencia ? <Fact label="Onde está" value={risk.evidencia.texto} /> : null}
      </dl>
      {risk.evidencia?.trecho ? <blockquote className="market-obs">“{risk.evidencia.trecho}”</blockquote> : null}
      {risk.o_que_fazer.length > 0 ? (
        <>
          <p className="dossier-history-title">O que fazer</p>
          <ol className="market-intel-reasons" aria-label={`O que fazer: ${risk.titulo}`}>
            {risk.o_que_fazer.map((a) => <li key={a}>{a}</li>)}
          </ol>
        </>
      ) : null}
    </Card>
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
