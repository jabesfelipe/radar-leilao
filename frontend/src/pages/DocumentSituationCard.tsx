import { Badge, Card } from '../components/ui'
import type { DocumentSituation } from '../services/documents'

const expectedTone: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  ANALISADO: 'success', ATENDIDO_POR_CONSULTA: 'success', RECEBIDO: 'info', INCOMPLETO: 'warning', PENDENTE: 'neutral',
}
const expectedLabel: Record<string, string> = {
  ANALISADO: 'Analisado', ATENDIDO_POR_CONSULTA: 'Atendido por consulta', RECEBIDO: 'Recebido', INCOMPLETO: 'Incompleto', PENDENTE: 'Pendente',
}

/** Situação documental (v1.0.14): o que chegou, o que foi analisado, o que é obrigatório e falta, e a próxima ação. */
export function DocumentSituationCard({ situation }: { situation: DocumentSituation }) {
  const c = situation.contagem
  return (
    <Card padding="lg" aria-label="Situação documental">
      <p className="dossier-history-title">Situação documental</p>
      <p className="market-obs">{situation.texto}</p>
      <p className="market-obs">
        <Badge size="sm" tone="info">{`Recebidos: ${c.recebidos}`}</Badge>{' '}
        <Badge size="sm" tone="success">{`Analisados: ${c.analisados}`}</Badge>{' '}
        <Badge size="sm" tone={c.incompletos ? 'warning' : 'neutral'}>{`Incompletos: ${c.incompletos}`}</Badge>{' '}
        <Badge size="sm" tone="neutral">{`Evidências: ${c.evidencias}`}</Badge>
      </p>
      <div className="hub-table-wrap"><table className="hub-table" aria-label="Documentos esperados">
        <thead><tr><th>Documento</th><th>Exigência</th><th>Situação</th><th>Por que importa</th><th>Próxima ação</th></tr></thead>
        <tbody>
          {situation.esperados.map((e) => (
            <tr key={e.chave}>
              <td>{e.nome}</td>
              <td>{e.obrigatorio ? 'Obrigatório' : 'Recomendado'}</td>
              <td><Badge size="sm" tone={e.obrigatorio && e.situacao === 'PENDENTE' ? 'danger' : expectedTone[e.situacao] ?? 'neutral'}>{expectedLabel[e.situacao] ?? e.situacao}</Badge></td>
              <td><small className="market-obs">{e.por_que}</small></td>
              <td><small className="market-obs">{e.proxima_acao ?? '—'}</small></td>
            </tr>
          ))}
        </tbody>
      </table></div>
      {situation.documentos.length > 0 ? (
        <ul className="market-intel-reasons" aria-label="Documentos analisados">
          {situation.documentos.map((d) => (
            <li key={d.id}>
              <strong>{d.nome}</strong>: {d.situacao_label} · {d.evidencias} evidência(s)
              {d.paginas_citadas.length ? ` · páginas citadas ${d.paginas_citadas.join(', ')}` : ''}
              {d.evidencias ? ` · confiança alta ${d.confianca.alta}, média ${d.confianca.media}, baixa ${d.confianca.baixa}` : ''}
              {d.pendencias.map((p) => <small key={p} className="market-obs"> · {p}</small>)}
            </li>
          ))}
        </ul>
      ) : null}
    </Card>
  )
}
