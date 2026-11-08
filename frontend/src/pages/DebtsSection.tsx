import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Coins, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import { formatMoney } from '../services/market'
import {
  estimateCondominium, getDebts, listDebtQueries,
  type AgeAlerts, type CondominiumEstimate, type DebtQueryRow, type DebtsView,
} from '../services/debts'

type DebtsSectionProps = { propertyId: number }

const NATURE_LABELS: Record<string, string> = {
  confirmados: 'Confirmados', informados: 'Informados', estimados: 'Estimados',
  despesas_previstas: 'Despesas previstas', nao_apurados: 'Não apurados',
}

const STATUS_TONE: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  CONCLUIDA: 'success', SEM_OCORRENCIA: 'neutral', REQUER_INTERVENCAO_MANUAL: 'warning',
  INDISPONIVEL: 'warning', ERRO: 'danger', PARCIAL: 'info', EM_EXECUCAO: 'info', PENDENTE: 'neutral',
}

export function DebtsSection({ propertyId }: DebtsSectionProps) {
  const [data, setData] = useState<DebtsView | null>(null)
  const [queries, setQueries] = useState<DebtQueryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Estimativa condominial
  const [monthly, setMonthly] = useState('')
  const [months, setMonths] = useState('')
  const [propertyAge, setPropertyAge] = useState('')
  const [ageKnown, setAgeKnown] = useState(true)
  const [estimate, setEstimate] = useState<CondominiumEstimate | null>(null)
  const [alerts, setAlerts] = useState<AgeAlerts | null>(null)
  const [estimating, setEstimating] = useState(false)
  const [estError, setEstError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [debts, q] = await Promise.all([getDebts(propertyId), listDebtQueries(propertyId)])
      setData(debts); setQueries(q.consultas)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os débitos.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void load() }, [load])

  const runEstimate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setEstimating(true); setEstError('')
    try {
      const res = await estimateCondominium(propertyId, {
        monthly_reference: monthly.trim() ? Number(monthly) : null,
        months_delinquent: months.trim() ? Number(months) : null,
        property_age_years: propertyAge.trim() ? Number(propertyAge) : null,
        age_known: ageKnown,
        persist: false,
      })
      setEstimate(res.estimativa); setAlerts(res.alertas_idade)
    } catch (cause) {
      setEstError(cause instanceof Error ? cause.message : 'Não foi possível calcular a estimativa.')
    } finally {
      setEstimating(false)
    }
  }

  const consolidation = data?.consolidacao

  return (
    <Section title="Débitos e despesas" description="Consolidação por natureza (confirmado ≠ estimado ≠ informado), consultas e estimativa condominial. Nenhuma consulta externa é executada." className="dossier-section">
      {loading ? (
        <LoadingState label="Carregando débitos…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : (
        <>
          {consolidation && (
            <Card padding="lg" className="market-quality">
              <p className="eyebrow">CONSOLIDAÇÃO POR NATUREZA</p>
              <dl className="dossier-facts">
                {Object.entries(NATURE_LABELS).map(([key, label]) => (
                  <div key={key}>
                    <dt>{label}</dt>
                    <dd>{formatMoney(consolidation.totais?.[key] ?? 0)} <span className="debts-count">({consolidation.contagens?.[key] ?? 0})</span></dd>
                  </div>
                ))}
                <div>
                  <dt>Exposição de passivo (com ressalva)</dt>
                  <dd><strong>{formatMoney(consolidation.exposicao_passivo_com_ressalva ?? 0)}</strong></dd>
                </div>
              </dl>
              {consolidation.ressalvas?.map((r) => <Alert key={r} tone="info">{r}</Alert>)}
            </Card>
          )}

          <Card padding="lg" className="dossier-form-card">
            <p className="eyebrow">ESTIMATIVA CONDOMINIAL (SEMPRE ESTIMADA)</p>
            <p className="wizard-muted">Idade do imóvel é contexto de incerteza, não prova de inadimplência. O período de inadimplência é um parâmetro explícito, nunca derivado da idade.</p>
            <form className="dossier-form" onSubmit={runEstimate} noValidate>
              <Input label="Valor mensal de referência (opcional)" type="number" step="0.01" value={monthly} onChange={(e) => setMonthly(e.target.value)} />
              <Input label="Meses de inadimplência (opcional)" type="number" value={months} onChange={(e) => setMonths(e.target.value)} />
              <Input label="Idade do imóvel em anos (opcional)" type="number" value={propertyAge} onChange={(e) => setPropertyAge(e.target.value)} />
              <label className="admin-check">
                <input type="checkbox" checked={ageKnown} onChange={(e) => setAgeKnown(e.target.checked)} />
                Idade conhecida (com evidência)
              </label>
              <div className="dossier-form-actions">
                {estError && <Alert tone="danger">{estError}</Alert>}
                <Button type="submit" loading={estimating}>Calcular estimativa</Button>
              </div>
            </form>
            {estimate && (
              <div className="debts-estimate">
                {estimate.possivel && estimate.cenarios ? (
                  <>
                    <dl className="dossier-facts">
                      <div><dt>Conservador</dt><dd>{formatMoney(estimate.cenarios.conservador)}</dd></div>
                      <div><dt>Provável</dt><dd>{formatMoney(estimate.cenarios.provavel)}</dd></div>
                      <div><dt>Otimista</dt><dd>{formatMoney(estimate.cenarios.otimista)}</dd></div>
                      <div><dt>Confiança</dt><dd><Badge tone={estimate.confianca === 'ALTA' ? 'success' : estimate.confianca === 'MEDIA' ? 'info' : 'warning'}>{estimate.confianca}</Badge></dd></div>
                    </dl>
                    {estimate.ressalva && <Alert tone="warning">{estimate.ressalva}</Alert>}
                  </>
                ) : (
                  <Alert tone="info">{estimate.motivo ?? 'Estimativa não calculável com os dados informados.'}</Alert>
                )}
              </div>
            )}
            {alerts && (
              <Alert tone={alerts.nivel ? 'warning' : 'info'}>
                {alerts.mensagem} {alerts.conclusivo ? '' : '(não conclusivo)'}
              </Alert>
            )}
          </Card>

          <Card padding="lg">
            <p className="eyebrow">HISTÓRICO DE CONSULTAS</p>
            {queries.length === 0 ? (
              <EmptyState title="Sem consultas" description="As consultas de débito aparecem aqui (manual/assistida)." icon={<Coins size={22} />} />
            ) : (
              <table className="admin-table">
                <thead><tr><th>Tipo</th><th>Provider</th><th>Modo</th><th>Status</th><th>Tentativas</th><th>Mensagem</th></tr></thead>
                <tbody>
                  {queries.map((q) => (
                    <tr key={q.id}>
                      <td>{q.debt_type_code}</td><td>{q.provider}</td><td>{q.mode}</td>
                      <td><Badge tone={STATUS_TONE[q.status] ?? 'neutral'}>{q.status}</Badge></td>
                      <td>{q.attempts}</td><td>{q.message ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </Section>
  )
}
