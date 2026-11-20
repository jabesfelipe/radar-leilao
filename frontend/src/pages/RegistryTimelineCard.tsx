import { useState } from 'react'
import { Alert, Badge, Button, Card, LoadingState } from '../components/ui'
import { getRegistryTimeline, type CurrentSituation, type RegistryTimeline, type TimelineEvent, type Titularity } from '../services/registration'

function formatDate(iso: string | null) {
  if (!iso) return 'Data não identificada'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function formatMoney(value: number | string) {
  const n = typeof value === 'string' ? Number(value) : value
  return Number.isFinite(n) ? n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : String(value)
}

/** Situação atual em destaque (revisão PR #8): quem é o dono hoje, antes do histórico. */
function CurrentSituationCard({ situation }: { situation: CurrentSituation }) {
  return (
    <section className="registry-current" aria-label="Situação atual do imóvel">
      <p className="dossier-history-title">PROPRIETÁRIO ATUAL</p>
      <p><strong>{situation.titular_atual ?? 'Não confirmado pela matrícula'}</strong>{situation.ato ? <small className="market-obs"> · {situation.ato}{situation.data ? `, ${formatDate(situation.data)}` : ''} · confiança {situation.confianca}</small> : null}</p>
      <p><strong>{situation.titulo}</strong></p>
      <p className="market-obs">{situation.texto}</p>
      {situation.atencao.length > 0 ? (
        <ul className="market-intel-reasons" aria-label="Pontos de atenção">
          {situation.atencao.map((a) => <li key={a}>{a}</li>)}
        </ul>
      ) : null}
    </section>
  )
}

function EventItem({ event }: { event: TimelineEvent }) {
  const people = event.envolvidos ?? event.partes.map((p) => ({ nome: p.nome, papel: p.papel_descricao }))
  return (
    <details className="dossier-timeline-item registry-event">
      <summary>
        <strong>{event.titulo_simples ?? event.tipo_descricao}</strong> · {formatDate(event.data)}
        <small className="market-obs"> {event.ato_descricao ?? `${event.ato} — ${event.tipo_descricao}`}</small>
        {event.conclusao_obra ? <> <Badge tone="info" size="sm">Conclusão de obra</Badge></> : null}
      </summary>
      {event.explicacao ? <p>{event.explicacao}</p> : null}
      {event.aviso_ocr ? <Alert tone="warning">{event.aviso_ocr}</Alert> : null}
      {people.length > 0 ? (
        <ul className="market-intel-reasons" aria-label={`Quem está envolvido no ato ${event.ato}`}>
          {people.map((p) => <li key={`${p.papel}-${p.nome}`}><strong>{p.papel}:</strong> {p.nome}</li>)}
        </ul>
      ) : <p className="market-obs">Nenhuma pessoa com papel declarado no texto deste ato.</p>}
      <dl className="dossier-facts">
        <div><dt>Ato registral</dt><dd>{event.ato_descricao ?? `${event.ato} — ${event.tipo_descricao}`}</dd></div>
        {event.datas && event.datas.length > 0 ? event.datas.map((d) => (
          <div key={`${d.tipo}-${d.data}-${d.data_texto}`}><dt>{d.tipo_descricao}</dt><dd>{d.data_texto}</dd></div>
        )) : <div><dt>Data citada no ato</dt><dd>{event.data_texto ?? 'Não identificada no texto'}</dd></div>}
        {event.protocolo ? <div><dt>Protocolo</dt><dd>{event.protocolo}</dd></div> : null}
        {event.valor ? <div><dt>Valor ({event.valor.rotulo})</dt><dd>{formatMoney(event.valor.valor)}</dd></div> : null}
        <div><dt>Documento</dt><dd>{event.documento?.nome ?? 'matrícula'}{event.pagina ? ` · página ${event.pagina}` : event.secao ? ` · ${event.secao}` : ''}</dd></div>
        {event.evidencia ? <div><dt>Confiança da leitura</dt><dd>{event.evidencia.confianca}</dd></div> : null}
      </dl>
      <p className="market-obs">Trecho da matrícula:</p>
      <blockquote className="market-obs">“{event.trecho}”</blockquote>
    </details>
  )
}

/** Titularidade (auditoria v6): titular atual pelo último ato x pessoas históricas, cada uma com papel, ato, trecho e confiança. */
function TitularityTable({ titularity }: { titularity: Titularity }) {
  return (
    <details className="registry-titularity">
      <summary>Quem aparece na matrícula e em que papel</summary>
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
      ) : <p className="market-obs">{titularity.texto}</p>}
      {titularity.aviso ? <p className="market-obs">{titularity.aviso}</p> : null}
    </details>
  )
}

/** Linha do tempo da matrícula: carregada sob demanda. Situação atual no topo; histórico do ato mais recente para o mais antigo. */
export function RegistryTimelineCard({ propertyId }: { propertyId: number }) {
  const [data, setData] = useState<RegistryTimeline | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const load = async () => {
    setLoading(true); setError('')
    try { setData(await getRegistryTimeline(propertyId)) } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível carregar a linha do tempo.') } finally { setLoading(false) }
  }
  const history = data ? (data.eventos_recentes_primeiro ?? [...(data.eventos ?? [])].reverse()) : []
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
          {data.situacao_atual ? <CurrentSituationCard situation={data.situacao_atual} /> : null}
          {data.titularidade ? <TitularityTable titularity={data.titularidade} /> : null}
          <p className="dossier-history-title">Histórico da matrícula (do mais recente para o mais antigo)</p>
          <p className="market-obs"><Badge tone={data.idade.estimada ? 'info' : 'neutral'} size="sm">Idade</Badge> {data.idade.texto}</p>
          {data.certidao ? <p className="market-obs"><Badge tone={data.certidao.data ? 'info' : 'warning'} size="sm">Certidão</Badge> {data.certidao.texto}</p> : null}
          {data.aviso_datas ? <p className="market-obs">{data.aviso_datas}</p> : null}
          {data.aviso_nomes ? <p className="market-obs">{data.aviso_nomes}</p> : null}
          <ol className="dossier-timeline" aria-label="Histórico da matrícula">
            {history.map((event) => <li key={`${event.ato}-${event.trecho.slice(0, 20)}`}><EventItem event={event} /></li>)}
          </ol>
        </>
      ) : null}
    </Card>
  )
}
