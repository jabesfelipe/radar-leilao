import { useState, type FormEvent } from 'react'
import { Alert, Badge, Button, Card } from '../components/ui'
import { getIptuGuidance, runDebtQuery, type IptuGuidance } from '../services/debts'
import { getFinance, saveFinanceAssumptions } from '../services/finance'
import { getIptuStatus, type IptuStatus } from '../services/investment'

const statusTone: Record<string, 'neutral' | 'warning' | 'danger' | 'info' | 'success'> = {
  CONSULTADO: 'success', CONSULTA_ASSISTIDA: 'info', PENDENTE_CONSULTA: 'warning', NAO_ENCONTRADO: 'warning', FALHA_CONSULTA: 'danger', NECESSITA_INFORMACAO: 'warning',
}

function toNumber(value: string): number | null {
  const clean = value.trim().replace(/\./g, '').replace(',', '.')
  if (!clean) return null
  const n = Number(clean)
  return Number.isFinite(n) && n >= 0 ? n : null
}

/** Consulta do IPTU (v1.0.14): situação, portal oficial e o registro do resultado lido no portal (consulta assistida).
 *  Nenhum dos portais permite automação; o resultado vai para Débitos e, o IPTU anual, para as premissas do Financeiro. */
export function IptuGuidanceCard({ propertyId }: { propertyId: number }) {
  const [data, setData] = useState<IptuGuidance | null>(null)
  const [status, setStatus] = useState<IptuStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')
  const [hasDebt, setHasDebt] = useState<'SIM' | 'NAO'>('SIM')
  const [amount, setAmount] = useState('')
  const [year, setYear] = useState('')
  const [annual, setAnnual] = useState('')
  const [note, setNote] = useState('')

  const loadStatus = async () => {
    try { setStatus(await getIptuStatus(propertyId)) } catch { setStatus(null) }
  }
  const load = async () => {
    setBusy(true); setError('')
    try { setData(await getIptuGuidance(propertyId)); await loadStatus() } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível carregar.') } finally { setBusy(false) }
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError(''); setSaved('')
    const debt = toNumber(amount)
    const yearly = toNumber(annual)
    if (hasDebt === 'SIM' && debt === null) { setError('Informe o valor do débito em aberto (ou marque "Sem débito em aberto").'); return }
    if (annual.trim() && yearly === null) { setError('IPTU anual inválido.'); return }
    setBusy(true)
    try {
      const origin = `Consulta assistida no portal da prefeitura${note.trim() ? `: ${note.trim()}` : ''}`
      await runDebtQuery(propertyId, {
        debt_type_code: 'IPTU', municipality_id: data?.municipality_id ?? null, identifier: data?.inscricao_imobiliaria ?? null,
        mensagem: note.trim() || null,
        ...(hasDebt === 'NAO' ? { sem_ocorrencia: true } : { itens: [{ updated_amount: debt, competence: year.trim() || null, origin, observations: note.trim() || null }] }),
      })
      if (yearly !== null) {
        const current = await getFinance(propertyId)
        await saveFinanceAssumptions(propertyId, { ...(current.premissas ?? {}), iptu_anual: yearly, iptu_anual_origem: origin.slice(0, 240) })
      }
      setSaved('Resultado registrado. Débitos, Financeiro e Riscos passam a usar este valor.')
      setAmount(''); setYear(''); setAnnual(''); setNote('')
      await loadStatus()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Não foi possível registrar o resultado.')
    } finally {
      setBusy(false)
    }
  }
  const g = data?.orientacao
  return (
    <Card padding="lg" aria-label="Consulta do IPTU no município">
      <div className="dossier-current-head">
        <p className="dossier-history-title">Consulta do IPTU no município</p>
        <Button variant="secondary" size="sm" onClick={() => void load()} loading={busy}>{data ? 'Atualizar' : 'Como consultar o IPTU'}</Button>
      </div>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {saved ? <Alert tone="success">{saved}</Alert> : null}
      {status ? (
        <p className="market-obs"><Badge tone={statusTone[status.status] ?? 'neutral'} size="sm">{status.status_label}</Badge> {status.texto}</p>
      ) : null}
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
      {data ? (
        <form className="market-intel-reasons" aria-label="Registrar o resultado da consulta do IPTU" onSubmit={(e) => void submit(e)}>
          <p className="dossier-history-title">Registrar o resultado da consulta</p>
          <p className="market-obs">Depois de consultar no portal, informe o que apareceu. Sem resultado registrado, o IPTU fica desconhecido (nunca zero).</p>
          <label><input type="radio" name="iptu-situacao" checked={hasDebt === 'SIM'} onChange={() => setHasDebt('SIM')} /> Há débito em aberto</label>{' '}
          <label><input type="radio" name="iptu-situacao" checked={hasDebt === 'NAO'} onChange={() => setHasDebt('NAO')} /> Sem débito em aberto</label>
          {hasDebt === 'SIM' ? (
            <>
              <label>Valor do débito em aberto (R$)<input aria-label="Valor do débito em aberto" value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" /></label>
              <label>Exercício(s)<input aria-label="Exercício" value={year} onChange={(e) => setYear(e.target.value)} placeholder="ex.: 2024-2025" /></label>
            </>
          ) : null}
          <label>IPTU anual do carnê (R$, opcional)<input aria-label="IPTU anual" value={annual} onChange={(e) => setAnnual(e.target.value)} inputMode="decimal" /></label>
          <label>Observação (opcional)<input aria-label="Observação da consulta" value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} /></label>
          <Button type="submit" size="sm" loading={busy}>Registrar resultado</Button>
        </form>
      ) : null}
    </Card>
  )
}
