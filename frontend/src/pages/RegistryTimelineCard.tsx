import { useState } from 'react'
import { Alert, Badge, Button, Card, LoadingState } from '../components/ui'
import { getRegistryTimeline, type RegistryTimeline, type TimelineEvent, type Titularity } from '../services/registration'

function formatDate(iso: string | null) {
  if (!iso) return 'Data não identificada'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function formatMoney(value: number | string) {
  const n = typeof value === 'string' ? Number(value) : value
  return Number.isFinite(n) ? n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : String(value)
}

function EventItem({ event }: { event: TimelineEvent }) {
  return (
    <details className="dossier-timeline-item registry-event">
      <summary>
        <strong>{event.ato}</strong> · {formatDate(event.data)} · {event.tipo_descricao}
        {event.conclusao_obra ? <> <Badge tone="info" size="sm">Conclusão de obra</Badge></> : null}
      </summary>
      <dl className="dossier-facts">
        <div><dt>Ato</dt><dd>{event.ato}</dd></div>
        <div><dt>Data citada no ato</dt><dd>{event.data_texto ?? 'Não identificada no texto'}</dd></div>
        <div><dt>Tipo</dt><dd>{event.tipo_descricao}</dd></div>
        {event.valor ? <div><dt>Valor ({event.valor.rotulo})</dt><dd>{formatMoney(event.valor.valor)}</dd></div> : null}
        {event.construtora ? <div><dt>Construtora</dt><dd>{event.construtora}</dd></div> : null}
        <div><dt>Documento</dt><dd>{event.documento?.nome ?? 'matrícula'}{event.pagina ? ` · página ${event.pagina}` : event.secao ? ` · ${event.secao}` : ''}</dd></div>
        <div><dt>Fonte</dt><dd>{event.fonte}</dd></div>
      </dl>
      {event.partes.length > 0 ? (
        <ul className="market-intel-reasons" aria-label={`Partes do ato ${event.ato}`}>
          {event.partes.map((p) => (
            <li key={`${p.papel}-${p.nome}`}><strong>{p.papel_descricao}:</strong> {p.nome} <small className="market-obs">({p.tipo_pessoa === 'FISICA' ? 'pessoa física' : 'pessoa jurídica'}; {p.como_identificado})</small></li>
          ))}
        </ul>
      ) : <p className="market-obs">Nenhuma parte com papel declarado no texto deste ato.</p>}
      <blockquote className="market-obs">“{event.trecho}”</blockquote>
    </details>
  )
}

/** Titularidade (auditoria v6): titular atual pelo último ato x pessoas históricas, cada uma com papel, ato, trecho e confiança. */
function TitularityTable({ titularity }: { titularity: Titularity }) {
  return (
    <div className="registry-titularity">
      <p className="market-obs">
        <Badge tone={titularity.titular_atual ? 'success' : 'warning'} size="sm">{titularity.titular_atual ? 'Titular atual' : 'Titularidade'}</Badge> {titularity.texto}
      </p>
      {titularity.partes.length > 0 ? (
        <table className="hub-table" aria-label="Titularidade e papéis na matrícula">
          <thead><tr><th>Nome</th><th>Papel</th><th>Ato</th><th>Data</th><th>Status</th><th>Confiança</th><th>Evidência</th></tr></thead>
          <tbody>
            {titularity.partes.map((p) => (
              <tr key={`${p.papel}-${p.nome}-${p.ato}`}>
                <td>{p.nome}</td>
                <td>{p.papel}{p.observacao ? <small className="market-obs"> {p.observacao}</small> : null}</td>
                <td>{p.ato ?? '—'}</td>
                <td>{p.data ? formatDate(p.data) : '—'}</td>
                <td><Badge tone={p.status === 'ATUAL' ? 'success' : 'neutral'} size="sm">{p.status === 'ATUAL' ? 'Atual' : 'Histórico'}</Badge></td>
                <td>{p.confianca}</td>
                <td><small className="market-obs">{p.fonte ? `${p.fonte}: ` : ''}{p.trecho ? `“${p.trecho.slice(0, 220)}”` : p.como_identificado}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {titularity.aviso ? <p className="market-obs">{titularity.aviso}</p> : null}
    </div>
  )
}

/** Linha do tempo da matrícula: carregada sob demanda (não altera as demais leituras da seção). */
export function RegistryTimelineCard({ propertyId }: { propertyId: number }) {
  const [data, setData] = useState<RegistryTimeline | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const load = async () => {
    setLoading(true); setError('')
    try { setData(await getRegistryTimeline(propertyId)) } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível carregar a linha do tempo.') } finally { setLoading(false) }
  }
  return (
    <Card padding="lg" className="dossier-history" aria-label="Linha do tempo da matrícula">
      <div className="dossier-current-head">
        <p className="dossier-history-title">Linha do tempo da matrícula</p>
        <Button variant="secondary" size="sm" onClick={() => void load()} loading={loading}>{data ? 'Atualizar' : 'Mostrar linha do tempo'}</Button>
      </div>
      {loading && !data ? <LoadingState label="Lendo os atos da matrícula…" /> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {data && !data.disponivel ? <Alert tone="info">{data.motivo ?? 'Sem matrícula com texto anexada.'}</Alert> : null}
      {data && data.disponivel ? (
        <>
          <p className="market-obs"><Badge tone={data.idade.estimada ? 'info' : 'neutral'} size="sm">Idade</Badge> {data.idade.texto}</p>
          {data.aviso_nomes ? <p className="market-obs">{data.aviso_nomes}</p> : null}
          {data.titularidade ? <TitularityTable titularity={data.titularidade} /> : null}
          <div className="dossier-timeline">
            {(data.eventos ?? []).map((event) => <EventItem key={`${event.ato}-${event.trecho.slice(0, 20)}`} event={event} />)}
          </div>
        </>
      ) : null}
    </Card>
  )
}
