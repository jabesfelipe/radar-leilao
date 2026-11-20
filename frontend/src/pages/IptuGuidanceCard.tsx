import { useState } from 'react'
import { Alert, Badge, Button, Card } from '../components/ui'
import { getIptuGuidance, type IptuGuidance } from '../services/debts'

/** Como consultar o IPTU do município (consulta manual assistida; nenhum dos portais permite automação). */
export function IptuGuidanceCard({ propertyId }: { propertyId: number }) {
  const [data, setData] = useState<IptuGuidance | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const load = async () => {
    setBusy(true); setError('')
    try { setData(await getIptuGuidance(propertyId)) } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível carregar.') } finally { setBusy(false) }
  }
  const g = data?.orientacao
  return (
    <Card padding="lg" aria-label="Consulta do IPTU no município">
      <div className="dossier-current-head">
        <p className="dossier-history-title">Consulta do IPTU no município</p>
        <Button variant="secondary" size="sm" onClick={() => void load()} loading={busy}>{data ? 'Atualizar' : 'Como consultar o IPTU'}</Button>
      </div>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {data && !g ? <Alert tone="info">{data.motivo ?? 'Sem orientação para o município.'}</Alert> : null}
      {g ? (
        <>
          <p className="market-obs"><Badge tone="warning" size="sm">Consulta manual assistida</Badge> {g.municipio}: {g.motivo}</p>
          {g.fonte ? <p className="market-obs">{g.fonte}{g.orgao ? ` · ${g.orgao}` : ''}</p> : null}
          {g.identificador ? <p className="market-obs">Identificador: {g.identificador}{data?.inscricao_imobiliaria ? ` · inscrição cadastrada: ${data.inscricao_imobiliaria}` : ''}</p> : null}
          {data?.titular_matricula ? <p className="market-obs">{data.titular_matricula.texto} {data.titular_matricula.aviso}</p> : null}
          {(g.exigencias ?? []).length > 0 ? <ul className="market-intel-reasons" aria-label="Exigências do portal">{g.exigencias!.map((e) => <li key={e}>{e}</li>)}</ul> : null}
          <ol className="market-intel-reasons" aria-label="Passo a passo">{g.passos.map((p) => <li key={p}>{p}</li>)}</ol>
          <ul className="market-intel-reasons" aria-label="Portais oficiais">
            {g.urls.map((u) => <li key={u}><a href={u} target="_blank" rel="noopener noreferrer">{u}</a></li>)}
          </ul>
          {g.aviso ? <Alert tone="info">{g.aviso}</Alert> : null}
        </>
      ) : null}
    </Card>
  )
}
