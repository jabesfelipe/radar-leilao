import { useCallback, useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, LoadingState, Section } from '../components/ui'
import {
  formatMoney, formatPercent, getInvestmentSummary,
  type FinanceRow, type InvestmentSummary, type MarketBlock, type TracedValue,
} from '../services/investment'

type Tone = 'neutral' | 'warning' | 'danger' | 'info' | 'success'

const recTone: Record<string, Tone> = { FAVORAVEL: 'success', ATENCAO_INVESTIGAR: 'warning', DESFAVORAVEL: 'danger', NAO_ARREMATAR: 'danger' }
const typeTone: Record<string, Tone> = { FATO: 'success', DADO_MANUAL: 'info', ESTIMATIVA: 'warning', INFERENCIA: 'warning', DESCONHECIDO: 'neutral' }
const iptuTone: Record<string, Tone> = {
  CONSULTADO: 'success', CONSULTA_ASSISTIDA: 'info', PENDENTE_CONSULTA: 'warning', NAO_ENCONTRADO: 'warning', FALHA_CONSULTA: 'danger', NECESSITA_INFORMACAO: 'warning',
}
const sampleTone: Record<string, Tone> = { INSUFICIENTE: 'danger', BAIXA: 'warning', MEDIA: 'info', ALTA: 'success' }

function TypeBadge({ value }: { value: TracedValue }) {
  return <Badge tone={typeTone[value.tipo] ?? 'neutral'} size="sm">{value.tipo_label}</Badge>
}

function Number_({ label, value, percent = false }: { label: string; value: TracedValue; percent?: boolean }) {
  return (
    <div>
      <dt>{label} <TypeBadge value={value} /></dt>
      <dd>{percent ? formatPercent(value.valor) : formatMoney(value.valor)}{value.provisorio ? ' (provisório)' : ''}</dd>
      {value.origem && value.tipo !== 'DESCONHECIDO' ? <small className="market-obs">{value.origem}</small> : null}
      {value.texto ? <small className="market-obs">{value.texto}</small> : null}
    </div>
  )
}

function FinanceGroup({ title, rows, empty }: { title: string; rows: FinanceRow[]; empty: string }) {
  return (
    <div>
      <p className="dossier-history-title">{title} ({rows.length})</p>
      {rows.length === 0 ? <p className="market-obs">{empty}</p> : (
        <ul className="market-intel-reasons">
          {rows.map((r) => (
            <li key={r.chave}>
              <strong>{r.descricao}</strong>: {r.valor != null ? formatMoney(r.valor) : r.valor_base != null ? `${formatMoney(r.valor_base)}${r.valor_conservador != null && r.valor_conservador !== r.valor_base ? ` a ${formatMoney(r.valor_conservador)}` : ''}` : 'sem valor'}
              {r.motivo ? <small className="market-obs"> · {r.motivo}</small> : r.origem ? <small className="market-obs"> · {r.origem}</small> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function MarketTable({ title, block }: { title: string; block: MarketBlock }) {
  return (
    <div>
      <p className="dossier-history-title">{title} <Badge tone={sampleTone[block.qualidade.nivel] ?? 'neutral'} size="sm">{block.qualidade.label}</Badge></p>
      <p className="market-obs">{block.qualidade.texto}</p>
      {block.quantidade_usada > 0 ? (
        <p className="market-obs">
          Média {formatMoney(block.media_total)} · mediana {formatMoney(block.mediana_total)} · R$/m² médio {formatMoney(block.m2_media)} · R$/m² mediano {formatMoney(block.m2_mediana)}
          {block.faixa ? ` · faixa ${formatMoney(block.faixa.min)} a ${formatMoney(block.faixa.max)} (${block.faixa_criterio})` : ''}
        </p>
      ) : null}
      {block.comparaveis.length > 0 ? (
        <table className="hub-table" aria-label={`Comparáveis: ${title}`}>
          <thead><tr><th>Anúncio</th><th>Valor</th><th>Área</th><th>R$/m²</th><th>Coleta</th><th>Similaridade</th><th>Uso</th></tr></thead>
          <tbody>
            {block.comparaveis.map((c) => (
              <tr key={c.id}>
                <td>{c.link ? <a href={c.link} target="_blank" rel="noopener noreferrer">{c.fonte || 'link'}</a> : (c.fonte || '—')}</td>
                <td>{formatMoney(c.valor)}</td>
                <td>{c.area_m2 != null ? `${c.area_m2} m²` : '—'}</td>
                <td>{c.valor_m2 != null ? formatMoney(c.valor_m2) : '—'}</td>
                <td>{c.data_coleta ?? '—'}</td>
                <td>{c.similaridade != null ? formatPercent(c.similaridade) : '—'}</td>
                <td>{c.usado ? 'Usado' : <small className="market-obs">{c.motivo_exclusao ?? 'Não usado'}</small>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  )
}

/** Resumo do investimento (v1.0.14): arrematar?, números com o tipo de cada dado, principal risco, pendências e próximas ações. */
export function InvestmentSummarySection({ propertyId }: { propertyId: number }) {
  const [data, setData] = useState<InvestmentSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await getInvestmentSummary(propertyId)) } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível carregar o resumo.') } finally { setLoading(false) }
  }, [propertyId])

  useEffect(() => { void load() }, [load])

  if (loading) return <Section title="Resumo do investimento" className="dossier-section"><LoadingState label="Montando o resumo…" /></Section>
  if (error || !data) {
    return (
      <Section title="Resumo do investimento" className="dossier-section">
        <Card padding="lg"><Alert tone="danger" title="Não foi possível carregar">{error || 'Sem dados.'}</Alert>
          <Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Tentar novamente</Button></Card>
      </Section>
    )
  }
  const { recomendacao: rec, numeros: n, iptu, condominio: condo, mercado, financeiro: fin } = data
  return (
    <Section title="Resumo do investimento" description="A resposta para a decisão: arrematar ou não, até quanto e o que falta saber." className="dossier-section">
      <Card padding="lg" aria-label="Recomendação">
        <p className="dossier-history-title">Recomendação <Badge tone={recTone[rec.codigo] ?? 'neutral'}>{rec.label}</Badge></p>
        <p><strong>Arrematar?</strong> {rec.arrematar}</p>
        {rec.motivos.length > 0 ? <ul className="market-intel-reasons" aria-label="Motivos da recomendação">{rec.motivos.map((m) => <li key={m}>{m}</li>)}</ul> : null}
        {rec.aviso_margem ? <Alert tone="warning">{rec.aviso_margem}</Alert> : null}
        {data.principal_risco ? <p><strong>Principal risco:</strong> {data.principal_risco}</p> : <p className="market-obs">Nenhum risco ativo identificado.</p>}
      </Card>

      <Card padding="lg" aria-label="Números do investimento">
        <dl className="dossier-facts">
          <Number_ label="Lance" value={n.lance} />
          <Number_ label="Preço máximo" value={n.preco_maximo} />
          <Number_ label="Valor de venda" value={n.valor_venda} />
          <Number_ label="Lucro estimado" value={n.lucro_estimado} />
          <Number_ label="ROI" value={n.roi} percent />
          <Number_ label="Margem" value={n.margem} percent />
          <Number_ label="Investimento total" value={n.investimento_total} />
        </dl>
        <p className="market-obs">Fato = documento ou fonte oficial; dado manual = informado por você; estimativa = calculado; desconhecido = ainda não levantado (nunca conta como zero).</p>
      </Card>

      {data.pendencias.length > 0 || data.proximas_acoes.length > 0 ? (
        <Card padding="lg" aria-label="Pendências e próximas ações">
          {data.pendencias.length > 0 ? (
            <>
              <p className="dossier-history-title">O que falta saber</p>
              <ul className="market-intel-reasons" aria-label="Pendências">{data.pendencias.map((p) => <li key={p}>{p}</li>)}</ul>
            </>
          ) : null}
          {data.proximas_acoes.length > 0 ? (
            <>
              <p className="dossier-history-title">Próximas ações (por prioridade)</p>
              <ol className="market-intel-reasons" aria-label="Próximas ações">{data.proximas_acoes.map((a) => <li key={`${a.tema}-${a.acao}`}><strong>{a.tema}:</strong> {a.acao}</li>)}</ol>
            </>
          ) : null}
        </Card>
      ) : null}

      <Card padding="lg" aria-label="IPTU">
        <p className="dossier-history-title">IPTU <Badge tone={iptuTone[iptu.status] ?? 'neutral'} size="sm">{iptu.status_label}</Badge></p>
        <p className="market-obs">{iptu.texto}</p>
        <dl className="dossier-facts">
          <Number_ label="Débito em aberto" value={iptu.debito_em_aberto} />
          <Number_ label="IPTU anual" value={iptu.valor_anual} />
        </dl>
        {!iptu.automatico && iptu.motivo_sem_automacao ? <p className="market-obs">Por que não é automático: {iptu.motivo_sem_automacao}</p> : null}
        {iptu.portal?.urls?.length ? <p className="market-obs">Portal: {iptu.portal.urls.map((u) => <a key={u} href={u} target="_blank" rel="noopener noreferrer">{u} </a>)}</p> : null}
        <p className="market-obs">Registre o resultado em Débitos e despesas &gt; Consulta do IPTU. {iptu.aviso}</p>
      </Card>

      <Card padding="lg" aria-label="Condomínio">
        <p className="dossier-history-title">Condomínio <Badge tone={condo.estimativa_insuficiente ? 'warning' : 'info'} size="sm">{condo.taxa_mensal.status_label}</Badge></p>
        <p className="market-obs">{condo.texto}</p>
        <dl className="dossier-facts">
          <Number_ label="Taxa mensal" value={condo.taxa_mensal} />
          <div>
            <dt>Dívida acumulada <Badge tone={typeTone[condo.divida_acumulada.tipo] ?? 'neutral'} size="sm">{condo.divida_acumulada.tipo_label}</Badge></dt>
            <dd>{condo.divida_acumulada.valor != null ? formatMoney(condo.divida_acumulada.valor)
              : condo.divida_acumulada.valor_base != null ? `${formatMoney(condo.divida_acumulada.valor_base)} a ${formatMoney(condo.divida_acumulada.valor_conservador)}` : 'Desconhecida'}</dd>
            {condo.divida_acumulada.origem ? <small className="market-obs">{condo.divida_acumulada.origem}</small> : null}
          </div>
        </dl>
        {condo.referencias ? (
          <p className="market-obs">
            Referências: {condo.referencias.quantidade} imóvel(is) parecido(s) · média {formatMoney(condo.referencias.media)} · mediana {formatMoney(condo.referencias.mediana)} ·
            faixa {formatMoney(condo.referencias.faixa.min)} a {formatMoney(condo.referencias.faixa.max)} · confiança {condo.confianca}
          </p>
        ) : null}
        {condo.mesmo_predio ? <p className="market-obs">{condo.mesmo_predio.status_label}: {condo.mesmo_predio.quantidade} anúncio(s), mediana {formatMoney(condo.mesmo_predio.mediana)}.</p> : null}
        <p className="market-obs">{condo.taxa_extra.texto}</p>
        <p className="market-obs">{condo.aviso}</p>
      </Card>

      <Card padding="lg" aria-label="Mercado">
        <p className="dossier-history-title">Mercado</p>
        <dl className="dossier-facts">
          <Number_ label="Valor de venda usado" value={mercado.valor_venda_usado} />
          <Number_ label="Aluguel estimado" value={mercado.aluguel_estimado} />
          <div><dt>Yield bruto</dt><dd>{mercado.yield_bruto_anual.texto}</dd></div>
          {mercado.liquidez ? <div><dt>Liquidez</dt><dd>{mercado.liquidez.classificacao} (confiança {mercado.liquidez.confianca})</dd></div> : null}
        </dl>
        <MarketTable title="Venda" block={mercado.venda} />
        <MarketTable title="Aluguel" block={mercado.aluguel} />
        <Alert tone="info">{mercado.busca_automatica.texto}</Alert>
      </Card>

      <Card padding="lg" aria-label="Financeiro por natureza">
        <p className="dossier-history-title">Custos por natureza</p>
        <p className="market-obs">{fin.texto}</p>
        <FinanceGroup title="Confirmado" rows={fin.confirmado} empty="Nenhum custo confirmado." />
        <FinanceGroup title="Estimado" rows={fin.estimado} empty="Nenhum custo estimado." />
        <FinanceGroup title="Desconhecido (fora da soma)" rows={fin.desconhecido} empty="Nenhum custo desconhecido." />
        <FinanceGroup title="Não incluído" rows={fin.nao_incluido} empty="Nenhum item excluído." />
      </Card>
    </Section>
  )
}
