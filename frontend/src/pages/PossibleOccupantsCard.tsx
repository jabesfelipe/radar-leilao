import { useState } from 'react'
import { Alert, Badge, Button, Card, LoadingState } from '../components/ui'
import { getPossibleOccupants, type PossibleOccupantsResponse } from '../services/market'

/** Pessoas identificadas nos documentos do imóvel (sugestão; não confirma ocupação). Carregado sob demanda. */
export function PossibleOccupantsCard({ propertyId }: { propertyId: number }) {
  const [data, setData] = useState<PossibleOccupantsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const load = async () => {
    setLoading(true); setError('')
    try { setData(await getPossibleOccupants(propertyId)) } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível carregar.') } finally { setLoading(false) }
  }
  return (
    <Card padding="lg" className="dossier-history" aria-label="Possíveis ocupantes identificados nos documentos">
      <div className="dossier-current-head">
        <p className="dossier-history-title">Possíveis ocupantes identificados nos documentos</p>
        <Button variant="secondary" size="sm" onClick={() => void load()} loading={loading}>{data ? 'Atualizar' : 'Ver possíveis ocupantes'}</Button>
      </div>
      {loading && !data ? <LoadingState label="Lendo os documentos…" /> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {data ? (
        <>
          <Alert tone="warning">{data.aviso}</Alert>
          {data.possiveis_ocupantes.length === 0 ? (
            <p className="market-obs">{data.motivo ?? 'Nenhuma pessoa física identificada nos documentos do imóvel.'}</p>
          ) : (
            <ul className="market-intel-reasons" aria-label="Lista de possíveis ocupantes">
              {data.possiveis_ocupantes.map((p) => (
                <li key={p.nome}>
                  <strong>{p.nome}</strong> {p.papeis.map((papel) => <Badge key={papel} tone="neutral" size="sm">{papel}</Badge>)}
                  {p.origens.map((o) => (
                    <details key={`${o.ato}-${o.papel}`}>
                      <summary>{o.documento ?? 'documento'} · {o.ato} ({o.tipo_ato}){o.data ? ` · ${o.data.split('-').reverse().join('/')}` : ''}</summary>
                      <small className="market-obs">{o.como_identificado}</small>
                      <blockquote className="market-obs">“{o.trecho}”</blockquote>
                    </details>
                  ))}
                </li>
              ))}
            </ul>
          )}
          <p className="market-obs">{data.observacao}</p>
        </>
      ) : null}
    </Card>
  )
}
