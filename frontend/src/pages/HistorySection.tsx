import { useCallback, useEffect, useState } from 'react'
import { Activity, History, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section } from '../components/ui'
import { getHistory, type AnalysisRecord, type DomainEvent } from '../services/history'

type HistorySectionProps = {
  propertyId: number
}

function formatDateTime(value?: string) {
  if (!value) return 'Data não informada'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('pt-BR')
}

export function HistorySection({ propertyId }: HistorySectionProps) {
  const [events, setEvents] = useState<DomainEvent[]>([])
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadHistory = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const history = await getHistory(propertyId)
      setEvents(history.events)
      setAnalyses(history.analyses)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o histórico.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadHistory() }, [loadHistory])

  const isEmpty = events.length === 0 && analyses.length === 0

  return (
    <Section title="Histórico" description="Eventos e versões de análise registrados para este imóvel." className="dossier-section">
      {loading ? (
        <LoadingState label="Carregando histórico…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadHistory()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : isEmpty ? (
        <Card padding="none"><EmptyState title="Nenhum histórico registrado" description="Ainda não há eventos ou análises registrados para este imóvel." icon={<History size={24} />} /></Card>
      ) : (
        <div className="history-groups">
          {analyses.length > 0 && (
            <div className="history-group">
              <p className="history-group-title"><Activity size={15} /> Versões de análise</p>
              <div className="history-timeline">
                {analyses.slice().reverse().map((analysis) => (
                  <div key={analysis.id} className="history-timeline-item">
                    <span className="history-timeline-dot" />
                    <Card padding="md" className="history-card">
                      <div className="history-card-head">
                        <strong>Análise v{analysis.version}</strong>
                        <span className="history-time">{formatDateTime(analysis.created_at)}</span>
                      </div>
                      <div className="history-card-meta">
                        {analysis.scope && <Badge tone="info" size="sm">{analysis.scope}</Badge>}
                        {analysis.agents_executed && analysis.agents_executed.length > 0 && <span>{analysis.agents_executed.length} agente(s)</span>}
                      </div>
                      {analysis.changes && <p className="history-changes">{analysis.changes}</p>}
                    </Card>
                  </div>
                ))}
              </div>
            </div>
          )}

          {events.length > 0 && (
            <div className="history-group">
              <p className="history-group-title"><History size={15} /> Eventos</p>
              <div className="history-timeline">
                {events.slice().reverse().map((event) => (
                  <div key={event.id} className="history-timeline-item">
                    <span className="history-timeline-dot" />
                    <Card padding="md" className="history-card">
                      <div className="history-card-head">
                        <strong>{event.event_type.split('_').join(' ')}</strong>
                        <span className="history-time">{formatDateTime(event.created_at)}</span>
                      </div>
                      <div className="history-card-meta">
                        {event.aggregate_type && <span>{event.aggregate_type}{event.aggregate_id != null ? ` #${event.aggregate_id}` : ''}</span>}
                        {event.affected_domains && event.affected_domains.length > 0 && <span>{event.affected_domains.join(', ')}</span>}
                      </div>
                    </Card>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Section>
  )
}
