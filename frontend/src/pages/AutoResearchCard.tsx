import { useState } from 'react'
import { Search } from 'lucide-react'
import { Alert, Badge, Button, Card } from '../components/ui'
import { formatMoney, runResearch, type ResearchRun } from '../services/investment'

const statusTone: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  SUCESSO: 'success', SEM_RESULTADO: 'warning', NAO_CONFIGURADO: 'neutral', ERRO: 'danger', LIMITE: 'warning',
}
const kindLabel: Record<string, string> = { VENDA: 'Venda', ALUGUEL: 'Aluguel', CONDOMINIO: 'Condomínio', IPTU_PORTAL: 'Portal do IPTU' }

/** Pesquisa automática do imóvel (v1.0.14): venda, aluguel, condomínio e portal do IPTU por API de pesquisa autorizada.
 *  Mostra o que foi pesquisado, o que virou comparável e por que o resto foi descartado. Sem provedor, diz o que configurar. */
export function AutoResearchCard({ propertyId, onDone }: { propertyId: number; onDone?: () => void }) {
  const [data, setData] = useState<ResearchRun | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const run = async () => {
    setBusy(true); setError('')
    try {
      const out = await runResearch(propertyId)
      setData(out)
      if (out.comparaveis_criados.length && onDone) onDone()
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível pesquisar.') } finally { setBusy(false) }
  }
  return (
    <Card padding="lg" aria-label="Pesquisa automática">
      <div className="dossier-current-head">
        <p className="dossier-history-title">Pesquisa automática (venda, aluguel, condomínio e IPTU)</p>
        <Button variant="secondary" size="sm" onClick={() => void run()} loading={busy}><Search size={14} /> {data ? 'Pesquisar de novo' : 'Pesquisar automaticamente'}</Button>
      </div>
      <p className="market-obs">Usa só APIs de pesquisa autorizadas e lê o título e o trecho devolvidos (sem abrir os portais). Preço de anúncio não é preço de venda fechada.</p>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {data ? (
        <>
          <p className="market-obs"><Badge tone={statusTone[data.status] ?? 'neutral'} size="sm">{data.status.split('_').join(' ')}</Badge> {data.texto ?? ''}</p>
          {data.consultas.length > 0 ? (
            <ul className="market-intel-reasons" aria-label="Consultas feitas">
              {data.consultas.map((c) => <li key={`${c.tipo}-${c.consulta}`}><strong>{kindLabel[c.tipo] ?? c.tipo}:</strong> “{c.consulta}” · {c.provedor} · {c.status.split('_').join(' ')} · {c.resultados} resultado(s)</li>)}
            </ul>
          ) : null}
          {data.comparaveis_criados.length > 0 ? (
            <>
              <p className="dossier-history-title">Comparáveis adicionados ({data.comparaveis_criados.length})</p>
              <ul className="market-intel-reasons">
                {data.comparaveis_criados.map((c) => <li key={c.id}>{kindLabel[c.tipo] ?? c.tipo}: {formatMoney(c.valor)}{c.area_m2 ? ` · ${c.area_m2} m²` : ''} · <a href={c.url} target="_blank" rel="noopener noreferrer">{c.fonte}</a> · confiança {c.confianca}</li>)}
              </ul>
            </>
          ) : null}
          {data.descartados.length > 0 ? (
            <details>
              <summary>Resultados não usados ({data.descartados.length})</summary>
              <ul className="market-intel-reasons">{data.descartados.slice(0, 20).map((d) => <li key={d.url}><a href={d.url} target="_blank" rel="noopener noreferrer">{d.titulo || d.url}</a>: {d.motivos.join(' ')}</li>)}</ul>
            </details>
          ) : null}
          {data.portais_iptu.length > 0 ? (
            <p className="market-obs">Portal do IPTU encontrado (confirme se é o oficial): {data.portais_iptu.map((p) => <a key={p.url} href={p.url} target="_blank" rel="noopener noreferrer">{p.dominio} </a>)}</p>
          ) : null}
        </>
      ) : null}
    </Card>
  )
}
