import { useState } from 'react'
import { Alert, Badge, Button, Card, Input } from '../components/ui'
import { formatMoney } from '../services/market'
import { estimateCondominiumFromRegistry, type RegistryCondoEstimate } from '../services/debts'

const SCENARIOS: { key: 'baixo' | 'provavel' | 'alto'; label: string }[] = [
  { key: 'baixo', label: 'Baixo' }, { key: 'provavel', label: 'Provável' }, { key: 'alto', label: 'Alto' },
]
const FEE_SOURCE: Record<string, string> = { INFORMADO: 'informado', COMPARAVEIS: 'mediana dos comparáveis', ADMIN: 'padrão do Admin' }

function pct(value: string | number) {
  const n = Number(value)
  return Number.isFinite(n) ? `${(n * 100).toFixed(0)}%` : String(value)
}

/** Estimativa condominial pelo período da matrícula (aquisição → consolidação). Calcula sob demanda; registrar alimenta o financeiro. */
export function CondoEstimateCard({ propertyId }: { propertyId: number }) {
  const [fee, setFee] = useState('')
  const [acq, setAcq] = useState('')
  const [cons, setCons] = useState('')
  const [result, setResult] = useState<RegistryCondoEstimate | null>(null)
  const [saved, setSaved] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const run = async (persist: boolean) => {
    setBusy(true); setError(''); setSaved(null)
    try {
      const out = await estimateCondominiumFromRegistry(propertyId, {
        monthly_reference: fee.trim() ? Number(fee) : undefined, acquisition_date: acq || undefined, consolidation_date: cons || undefined, persist,
      })
      setResult(out.estimativa); setSaved(out.estimativa_id)
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível calcular.') } finally { setBusy(false) }
  }
  const m = result?.memoria_calculo
  return (
    <Card padding="lg" aria-label="Estimativa condominial pela matrícula">
      <p className="dossier-history-title">Estimativa condominial pela matrícula</p>
      <p className="market-obs">Período entre a aquisição e a consolidação lidas na matrícula, com cenários e encargos configuráveis em Admin &gt; Premissas financeiras. O período não prova inadimplência.</p>
      <div className="dossier-form">
        <Input label="Condomínio mensal (opcional)" type="number" step="0.01" value={fee} onChange={(e) => setFee(e.target.value)} hint="Sem valor: mediana dos comparáveis ou padrão do Admin." />
        <Input label="Data de aquisição (opcional)" type="date" value={acq} onChange={(e) => setAcq(e.target.value)} hint="Sem data: a da matrícula." />
        <Input label="Data de consolidação (opcional)" type="date" value={cons} onChange={(e) => setCons(e.target.value)} hint="Sem data: a da matrícula." />
        <div className="dossier-form-actions">
          <Button variant="secondary" onClick={() => void run(false)} loading={busy}>Calcular pela matrícula</Button>
          <Button onClick={() => void run(true)} disabled={busy}>Registrar estimativa da matrícula</Button>
        </div>
      </div>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {result ? <Alert tone="warning">{result.aviso}</Alert> : null}
      {result && !result.possivel ? <Alert tone="info">{result.motivo}</Alert> : null}
      {saved != null ? <Alert tone="success">Estimativa registrada (nº {saved}). A composição de custos passa a usar o cenário provável no base e o alto no conservador.</Alert> : null}
      {result?.possivel && m && result.cenarios_detalhe ? (
        <>
          <p className="market-obs">
            <Badge tone="info" size="sm">Confiança {result.confianca}</Badge>{' '}
            Condomínio mensal {formatMoney(m.valor_mensal_referencia)} ({FEE_SOURCE[m.origem_valor_mensal ?? ''] ?? m.origem_valor_mensal}); aquisição {m.data_aquisicao} ({m.origem_data_aquisicao});
            consolidação {m.data_consolidacao} ({m.origem_data_consolidacao}); período {m.periodo_meses} meses, considerado {m.periodo_considerado_meses} (teto {m.teto_periodo_meses}).
          </p>
          <table className="admin-table" aria-label="Cenários da estimativa condominial">
            <thead><tr><th>Cenário</th><th>Fator</th><th>Meses</th><th>Principal</th><th>Multa</th><th>Juros</th><th>Correção</th><th>Dívida potencial</th><th>Comprador</th><th>Vendedor/Caixa</th><th>No financeiro</th></tr></thead>
            <tbody>
              {SCENARIOS.map(({ key, label }) => {
                const s = result.cenarios_detalhe![key]
                return (
                  <tr key={key}>
                    <td>{label}</td><td>{pct(s.fator)}</td><td>{s.meses_em_atraso}</td><td>{formatMoney(s.principal)}</td><td>{formatMoney(s.multa)}</td>
                    <td>{formatMoney(s.juros)}</td><td>{formatMoney(s.correcao)}</td><td>{formatMoney(s.divida_potencial)}</td>
                    <td>{formatMoney(s.responsabilidade_comprador)}</td><td>{formatMoney(s.responsabilidade_caixa)}</td>
                    <td>{s.valor_no_financeiro == null ? 'não usado' : formatMoney(s.valor_no_financeiro)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {result.regra_venda?.origem ? <p className="market-obs">Regra da venda aplicada depois da estimativa: {result.regra_venda.origem}{result.regra_venda.limite != null ? `; limite ${formatMoney(result.regra_venda.limite)}` : ''}.</p> : null}
          <p className="market-obs">Fórmula: {m.formula}.</p>
          <p className="market-obs">{m.nota}</p>
        </>
      ) : null}
    </Card>
  )
}
