import { useCallback, useEffect, useState } from 'react'
import { ExternalLink, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card } from '../components/ui'
import { formatMoney, formatPercent, getMarketIntelligence, type IntelComparable, type IntelCost, type IntelEstimate, type IntelScenario, type MarketIntelligence } from '../services/market'

// v1.0.8: inteligência de mercado e viabilidade. Separa visualmente o que é INFORMADO (confirmado), ESTIMADO e PENDENTE.
const STATUS_TONE: Record<string, 'success' | 'info' | 'warning' | 'neutral'> = { INFORMADO: 'success', ESTIMADO: 'info', PENDENTE: 'warning', NAO_APLICAVEL: 'neutral' }
const STATUS_LABEL: Record<string, string> = { INFORMADO: 'Confirmado', ESTIMADO: 'Estimado', PENDENTE: 'Pendente', NAO_APLICAVEL: 'Não aplicável' }
// Natureza do valor que ENTROU no cenário: confirmado ≠ estimado ≠ reserva ≠ teto de responsabilidade da Caixa.
const KIND_LABEL: Record<string, string> = {
  CONFIRMADO: 'Confirmado', ESTIMADO: 'Estimado', RESERVA: 'Reserva (custo pendente)', RESERVA_MANUAL: 'Reserva manual (custo pendente)',
  TETO_CAIXA: 'Teto Caixa (dívida pendente)', NAO_APLICAVEL: 'Não aplicável', FORA_DA_SOMA: 'Fora da soma',
}
const RESULT_TONE: Record<string, 'success' | 'danger' | 'warning'> = { FAVORAVEL: 'success', DESFAVORAVEL: 'danger', INCONCLUSIVO: 'warning' }
const RESULT_LABEL: Record<string, string> = { FAVORAVEL: 'Favorável', DESFAVORAVEL: 'Desfavorável', INCONCLUSIVO: 'Inconclusivo' }

function isIntelligence(payload: unknown): payload is MarketIntelligence {
  const p = payload as MarketIntelligence | null
  return Boolean(p && p.valores && p.venda && p.conclusao && Array.isArray(p.cenarios))
}

export function MarketIntelligencePanel({ propertyId, refreshKey = 0 }: { propertyId: number; refreshKey?: number }) {
  const [data, setData] = useState<MarketIntelligence | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const payload = await getMarketIntelligence(propertyId)
      setData(isIntelligence(payload) ? payload : null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar a inteligência de mercado.')
    }
  }, [propertyId])

  useEffect(() => { void load() }, [load, refreshKey])

  if (error) {
    return (
      <Card padding="lg" className="market-intel">
        <Alert tone="danger" title="Inteligência de mercado indisponível">{error}</Alert>
        <Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Recarregar inteligência de mercado</Button>
      </Card>
    )
  }
  if (!data) return null
  const { valores: v, conclusao: c } = data
  return (
    <Card padding="lg" className="market-intel" aria-label="Inteligência de mercado">
      <div className="finance-card-head">
        <strong>Inteligência de mercado e viabilidade</strong>
        <Badge tone={RESULT_TONE[c.resultado] ?? 'warning'}>{RESULT_LABEL[c.resultado] ?? c.resultado}</Badge>
      </div>
      <ul className="market-intel-reasons">
        {c.motivos.map((m) => <li key={m}>{m}</li>)}
        {c.bloqueios.map((b) => <li key={b}>{b}</li>)}
      </ul>
      {(c.ressalvas ?? []).length > 0 && (
        <ul className="market-intel-reasons" aria-label="Ressalvas">{(c.ressalvas ?? []).map((r) => <li key={r}>Ressalva: {r}</li>)}</ul>
      )}
      <p className="market-obs" aria-label="Legenda">
        <Badge size="sm" tone="success">Confirmado</Badge> valor informado ou cadastrado · <Badge size="sm" tone="info">Estimado</Badge> calculado por premissa declarada ·{' '}
        <Badge size="sm" tone="warning">Pendente</Badge> sem valor real: entra por reserva/teto identificado ou fica fora da soma (cenário incompleto).
      </p>

      {v.venda_preliminar ? (
        <Alert tone="warning">
          <Badge size="sm" tone="warning">{v.venda_preliminar.selo}</Badge> Valor de venda preliminar estimado: <strong>{formatMoney(v.venda_preliminar.valor)}</strong>{' '}
          = avaliação {formatMoney(v.venda_preliminar.avaliacao)} × fator {formatPercent(v.venda_preliminar.fator)} ({v.venda_preliminar.fator_origem}).
          Confiança: Baixa. Não há comparáveis suficientes. {v.venda_preliminar.observacao}
        </Alert>
      ) : null}
      <dl className="dossier-facts">
        <Fact label="Valor de mercado estimado" value={v.valor_mercado_estimado == null ? (data.venda.qualidade_amostra?.nivel === 'INSUFICIENTE' ? 'AMOSTRA INSUFICIENTE: sem valor de mercado' : 'Sem estimativa pontual') : formatMoney(v.valor_mercado_estimado)} />
        {data.venda.qualidade_amostra ? <Fact label="Qualidade da amostra (venda)" value={`${data.venda.qualidade_amostra.label}: ${data.venda.qualidade_amostra.texto}`} /> : null}
        {data.aluguel.qualidade_amostra ? <Fact label="Qualidade da amostra (aluguel)" value={data.aluguel.qualidade_amostra.label} /> : null}
        <Fact label="Faixa de venda" value={v.faixa_venda ? `${formatMoney(v.faixa_venda.min)} a ${formatMoney(v.faixa_venda.max)}` : 'Sem dados'} />
        <Fact label="Confiança (venda)" value={`${data.venda.confianca} · ${data.venda.quantidade_usada} comparável(is)`} />
        <Fact label="Preço/m² anunciado (mediana)" value={formatMoney(v.preco_m2_anunciado_mediana)} />
        <Fact label="Preço/m² estimado (mediana)" value={formatMoney(v.preco_m2_estimado_mediana)} />
        <Fact label={v.aluguel_indicativo ? 'Aluguel (indicativo)' : 'Aluguel estimado'} value={formatMoney(v.aluguel_estimado)} />
        <Fact label="Confiança (aluguel)" value={`${data.aluguel.confianca} · ${data.aluguel.quantidade_usada} comparável(is)`} />
        <Fact label="Desconto sobre a avaliação" value={formatPercent(v.desconto_sobre_avaliacao)} />
        <Fact label="Desconto sobre o mercado estimado" value={formatPercent(v.desconto_sobre_mercado)} />
        <Fact label="Liquidez" value={`${data.liquidez.classificacao} (confiança ${data.liquidez.confianca})`} />
        <Fact label="Preço máximo recomendado" value={data.preco_maximo.recomendado == null ? 'Não calculado' : `${formatMoney(data.preco_maximo.recomendado)}${data.preco_maximo.provisorio ? ' (provisório)' : ''}`} />
      </dl>
      <p className="market-obs">{v.observacao_descontos} {data.preco_maximo.criterio}.</p>
      {[...data.venda.avisos, ...data.aluguel.avisos].map((a) => <Alert key={a} tone="warning">{a}</Alert>)}
      {(data.venda.limitacoes ?? []).length > 0 && <>
        <h4>Limitações da amostra de venda</h4>
        <ul className="market-intel-reasons">{(data.venda.limitacoes ?? []).map((l) => <li key={l}>{l}</li>)}</ul>
      </>}

      <h4>Cenários</h4>
      <div className="hub-table-wrap">
        <table className="hub-table">
          <thead><tr><th>Cenário</th><th>Venda</th><th>Investimento</th><th>Corretagem</th><th>IR</th><th>Resultado</th><th>ROI</th><th>Margem de segurança</th><th>Aluguel bruto/líquido (a.a.)</th><th>Fora da soma</th></tr></thead>
          <tbody>{data.cenarios.map((s) => (
            <tr key={s.cenario}>
              <td>{s.cenario} · {s.prazo_meses} meses{s.completo === false ? <> <Badge size="sm" tone="warning">Incompleto</Badge></> : null}</td>
              <td>{formatMoney(s.valor_venda)}</td><td>{formatMoney(s.investimento_total)}</td>
              <td>{formatMoney(s.corretagem_venda ?? null)}</td><td>{formatMoney(s.tributo_venda ?? null)}</td>
              <td>{formatMoney(s.resultado_liquido)}</td><td>{formatPercent(s.roi)}</td><td>{formatPercent(s.margem_seguranca)}</td>
              <td>{s.rentabilidade_aluguel ? `${formatPercent(s.rentabilidade_aluguel.bruta_anual)} / ${formatPercent(s.rentabilidade_aluguel.liquida_anual)}` : 'Sem dados'}</td>
              <td>{s.custos_pendentes_nao_incluidos.length ? s.custos_pendentes_nao_incluidos.join(', ') : 'Nenhum'}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>

      {data.preco_maximo.por_cenario && <>
        <h4>Preço máximo por cenário</h4>
        <div className="hub-table-wrap">
          <table className="hub-table" aria-label="Preço máximo por cenário">
            <thead><tr><th>Cenário</th><th>Preço máximo</th><th>ROI no teto</th><th>Situação</th><th>Com os itens fora da soma no teto</th></tr></thead>
            <tbody>{Object.values(data.preco_maximo.por_cenario).map((m) => (
              <tr key={m.cenario}>
                <td>{m.cenario}</td>
                <td>{m.preco_maximo == null ? 'Não calculado' : `${formatMoney(m.preco_maximo)}${m.provisorio ? ' (provisório)' : ''}`}</td>
                <td>{formatPercent(m.roi_no_teto ?? null)}</td>
                <td>{m.provisorio ? <Badge size="sm" tone="warning">Provisório: não use como lance</Badge> : m.definitivo ? <Badge size="sm" tone="success">Definitivo</Badge> : m.razao}
                  {m.pendencias.length > 0 ? <small className="market-obs"> {m.pendencias.join(' ')}</small> : null}</td>
                <td>{m.com_pendencias_no_teto?.preco_maximo != null
                  ? <>{formatMoney(m.com_pendencias_no_teto.preco_maximo)} <small className="market-obs">({m.com_pendencias_no_teto.itens.join(', ')} no teto)</small></>
                  : '—'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </>}

      {data.cenarios.map((s) => <ScenarioComposition key={`comp-${s.cenario}`} scenario={s} />)}

      <h4>Custos de aquisição e posse</h4>
      <div className="hub-table-wrap">
        <table className="hub-table">
          <thead><tr><th>Item</th><th>Valor real</th><th>Situação</th><th>Base e otimista</th><th>Conservador</th><th>Origem</th></tr></thead>
          <tbody>{data.custos.map((cost) => (
            <tr key={cost.chave}>
              <td>{cost.descricao}{cost.observacao ? <small className="market-obs"> {cost.observacao}</small> : null}
                {cost.limite_responsabilidade != null || cost.divida_total != null ? <CaixaDebt cost={cost} /> : null}</td>
              <td>{cost.valor == null ? 'Não informado' : formatMoney(cost.valor)}</td>
              <td><Badge size="sm" tone={STATUS_TONE[cost.status] ?? 'neutral'}>{STATUS_LABEL[cost.status] ?? cost.status}</Badge></td>
              <td>{cost.valor_base == null ? (cost.status === 'PENDENTE' ? 'Fora da soma' : '—') : `${formatMoney(cost.valor_base)}${cost.valores_anuais ? '/ano' : ''}`}{cost.status === 'PENDENTE' && cost.tratamento_base ? <small className="market-obs"> {cost.tratamento_base}</small> : null}</td>
              <td>{cost.valor_conservador == null ? (cost.status === 'PENDENTE' ? 'Fora da soma' : '—') : `${formatMoney(cost.valor_conservador)}${cost.valores_anuais ? '/ano' : ''}`}{cost.status === 'PENDENTE' && cost.tratamento_conservador ? <small className="market-obs"> {cost.tratamento_conservador}</small> : null}</td>
              <td>{cost.origem}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>

      <ComparablesTable title="Comparáveis de venda" estimate={data.venda} />
      <ComparablesTable title="Comparáveis de aluguel" estimate={data.aluguel} />

      <h4>Liquidez</h4>
      <ul>{data.liquidez.justificativa.map((j) => <li key={j}>{j}</li>)}<li>{data.liquidez.prazo_observacao}</li></ul>

      <h4>Premissas</h4>
      <ul className="market-intel-premises">
        {Object.entries(data.premissas).map(([key, p]) => <li key={key}>{p.descricao}: <strong>{p.valor}</strong> <small>({p.origem})</small></li>)}
      </ul>
      <p className="market-obs">Calculado em {data.data_calculo}. Valores de anúncio são preços pedidos, não negócios fechados.</p>
    </Card>
  )
}

// Composição reprodutível: soma dos itens = investimento; venda − corretagem − IR − investimento = resultado.
function ScenarioComposition({ scenario: s }: { scenario: IntelScenario }) {
  const c = s.composicao
  if (!c) return null
  const included = c.itens.filter((i) => i.incluido)
  const excluded = c.itens.filter((i) => !i.incluido)
  const r = s.rentabilidade_aluguel
  return (
    <details className="market-intel-composition">
      <summary>Composição do cenário {s.cenario}{s.completo === false ? ' (incompleto: há custo sem valor fora da soma)' : ''}</summary>
      <table className="hub-table">
        <tbody>
          {included.map((i) => (
            <tr key={i.chave}>
              <td>{i.descricao} <Badge size="sm" tone={STATUS_TONE[i.status] ?? 'neutral'}>{KIND_LABEL[i.tipo_valor ?? ''] ?? (i.status === 'PENDENTE' ? 'Reserva (pendente)' : (STATUS_LABEL[i.status] ?? i.status))}</Badge>{' '}
                <small>({i.base_valor}{i.dedutivel_ir ? '; deduz do IR' : ''})</small></td>
              <td>{formatMoney(i.valor)}</td>
            </tr>
          ))}
          <tr><th>= Investimento total</th><th>{formatMoney(c.investimento_total)}</th></tr>
          {c.venda_bruta != null && <>
            <tr><td>Venda estimada</td><td>{formatMoney(c.venda_bruta)}</td></tr>
            <tr><td>− Corretagem na venda ({formatPercent(c.corretagem_venda?.percentual)})</td><td>{formatMoney(c.corretagem_venda?.valor)}</td></tr>
            <tr><td>= Venda líquida</td><td>{formatMoney(c.venda_liquida)}</td></tr>
            <tr><th colSpan={2}>Memória do IR sobre ganho de capital</th></tr>
            {(c.itens_dedutiveis_ir ?? []).map((d) => <tr key={`ded-${d.descricao}`}><td>Custo dedutível: {d.descricao}</td><td>{formatMoney(d.valor)}</td></tr>)}
            <tr><td>= Custo de aquisição dedutível</td><td>{formatMoney(c.custo_aquisicao_dedutivel_ir)}</td></tr>
            {(c.itens_nao_dedutiveis_ir ?? []).length > 0 && (
              <tr><td colSpan={2}><small>Não reduzem a base do IR: {(c.itens_nao_dedutiveis_ir ?? []).map((d) => `${d.descricao} (${formatMoney(d.valor)})`).join(', ')}.</small></td></tr>
            )}
            <tr><td>Base do IR (venda líquida − custo de aquisição dedutível)</td><td>{formatMoney(c.base_ir)}</td></tr>
            <tr><td>− IR sobre ganho de capital ({formatPercent(c.ir_ganho_capital?.aliquota)} × base)</td><td>{formatMoney(c.ir_ganho_capital?.valor)}</td></tr>
            <tr><td>− Investimento total</td><td>{formatMoney(c.investimento_total)}</td></tr>
            <tr><th>= Resultado líquido</th><th>{formatMoney(c.resultado_liquido)}</th></tr>
            <tr><td>ROI (resultado ÷ investimento)</td><td>{formatPercent(s.roi)}</td></tr>
            <tr><td>Venda de equilíbrio (resultado zero)</td><td>{formatMoney(c.venda_equilibrio)}</td></tr>
          </>}
          <tr><td>Despesas financeiras</td><td>{c.despesas_financeiras.observacao}</td></tr>
        </tbody>
      </table>
      {excluded.length > 0 && (
        <Alert tone="warning" title="Fora da soma (sem valor; não contados como zero)">
          {excluded.map((i) => i.teto_conservador != null ? `${i.descricao} (teto/reserva conhecido: ${formatMoney(i.teto_conservador)})` : i.descricao).join(', ')}.
        </Alert>
      )}
      {s.efeito_pendencias_no_teto && <PendingAtCeiling effect={s.efeito_pendencias_no_teto} />}
      {(s.impacto_reservas ?? []).length > 0 && (
        <>
          <strong>Impacto de cada reserva neste cenário</strong>
          <table className="hub-table" aria-label={`Impacto das reservas ${s.cenario}`}>
            <thead><tr><th>Reserva</th><th>Tipo</th><th>Investimento</th><th>Resultado</th><th>ROI</th><th>Preço máximo</th></tr></thead>
            <tbody>{(s.impacto_reservas ?? []).map((i) => (
              <tr key={i.chave}>
                <td>{i.descricao} <small>({i.base_valor})</small></td><td>{i.tipo}</td>
                <td>+{formatMoney(i.efeito_investimento)}</td><td>{formatMoney(i.efeito_resultado)}</td>
                <td>{i.efeito_roi == null ? '—' : `${(Number(i.efeito_roi) * 100).toFixed(2).replace('.', ',')} p.p.`}</td>
                <td>{formatMoney(i.efeito_preco_maximo)}</td>
              </tr>
            ))}</tbody>
          </table>
        </>
      )}
      {s.premissas && s.premissas.tratamento_pendencias.length > 0 && (
        <><strong>Premissas das pendências neste cenário</strong><ul>{s.premissas.tratamento_pendencias.map((p) => <li key={p}>{p}</li>)}</ul></>
      )}
      {c.ir_ganho_capital && <p className="market-obs">{c.ir_ganho_capital.observacao}</p>}
      {r && (
        <>
          <strong>Locação (tese alternativa, {r.aluguel_indicativo ? 'aluguel INDICATIVO' : 'aluguel estimado'})</strong>
          <table className="hub-table" aria-label={`Locação ${s.cenario}`}>
            <tbody>
              <tr><td>Aluguel mensal × 12</td><td>{formatMoney(r.receita_bruta_anual ?? null)}</td></tr>
              <tr><td>Recebido com vacância</td><td>{formatMoney(r.receita_com_vacancia ?? null)}</td></tr>
              <tr><td>− Taxa de administração</td><td>{formatMoney(r.taxa_administracao ?? null)}</td></tr>
              <tr><td>− Condomínio nos meses vagos</td><td>{formatMoney(r.condominio_na_vacancia ?? null)}</td></tr>
              <tr><td>− IPTU nos meses vagos</td><td>{r.iptu_na_vacancia == null ? 'Pendente' : formatMoney(r.iptu_na_vacancia)}</td></tr>
              <tr><th>= Resultado anual antes do IR</th><th>{formatMoney(r.resultado_anual_antes_ir ?? null)}</th></tr>
              <tr><td>Investimento de aquisição e preparação</td><td>{formatMoney(r.investimento_base ?? null)}</td></tr>
              <tr><td>Rentabilidade bruta / líquida (a.a.)</td><td>{formatPercent(r.bruta_anual)} / {formatPercent(r.liquida_anual)}</td></tr>
            </tbody>
          </table>
          <p className="market-obs">{r.premissas}.{(r.pendencias ?? []).length > 0 ? ` Pendências: ${(r.pendencias ?? []).join(', ')}.` : ''}</p>
        </>
      )}
      <p className="market-obs">{c.formula}.</p>
    </details>
  )
}

// Memória explícita do "e se as pendências chegarem ao teto": cada item somado, IR adicional e conferência da conta.
function PendingAtCeiling({ effect: e }: { effect: NonNullable<IntelScenario['efeito_pendencias_no_teto']> }) {
  return (
    <>
      <strong>Se os itens fora da soma chegarem ao teto/reserva conhecido</strong>
      <table className="hub-table" aria-label="Pendências no teto">
        <tbody>
          <tr><td>Resultado deste cenário (sem esses itens)</td><td>{formatMoney(e.resultado_atual ?? null)}</td></tr>
          {(e.detalhe ?? []).map((d) => (
            <tr key={d.chave}><td>− {d.descricao} <small>({d.tipo === 'TETO_CAIXA' ? 'teto de responsabilidade Caixa' : 'reserva'}{d.dedutivel_ir ? '; deduz do IR' : '; não deduz do IR'})</small></td>
              <td>{formatMoney(d.valor)}</td></tr>
          ))}
          <tr><td>− IR adicional</td><td>{formatMoney(e.ir_adicional ?? null)}</td></tr>
          <tr><th>= Resultado com os itens no teto</th><th>{formatMoney(e.resultado_se_no_teto)}</th></tr>
        </tbody>
      </table>
      {(e.sem_teto_conhecido ?? []).length > 0 && (
        <p className="market-obs">Continuam fora da soma, sem teto conhecido: {(e.sem_teto_conhecido ?? []).join(', ')}. O resultado real pode ser menor.</p>
      )}
    </>
  )
}

function CaixaDebt({ cost }: { cost: IntelCost }) {
  return (
    <small className="market-obs" aria-label={`Regra Caixa: ${cost.descricao}`}>
      {' '}Dívida total: {cost.divida_total == null ? 'desconhecida' : formatMoney(cost.divida_total)} · Limite do comprador:{' '}
      {cost.limite_responsabilidade == null ? 'sem regra' : formatMoney(cost.limite_responsabilidade)} · Responsabilidade do comprador:{' '}
      {cost.responsabilidade_comprador == null ? 'a apurar' : formatMoney(cost.responsabilidade_comprador)} · Assumido pela Caixa:{' '}
      {cost.assumido_caixa == null ? 'a apurar' : formatMoney(cost.assumido_caixa)}
      {cost.premissa_conservadora ? <> · {cost.premissa_conservadora}</> : null}
    </small>
  )
}

function ComparablesTable({ title, estimate }: { title: string; estimate: IntelEstimate }) {
  if (!estimate.comparaveis.length) return <><h4>{title}</h4><p className="market-obs">Nenhum comparável cadastrado.</p></>
  return (
    <>
      <h4>{title} ({estimate.quantidade_usada} usados de {estimate.quantidade_total})</h4>
      <div className="hub-table-wrap">
        <table className="hub-table">
          <thead><tr><th>Região</th><th>Valor</th><th>Área</th><th>R$/m²</th><th>Tipo de preço</th><th>Similaridade</th><th>Situação</th><th>Fonte</th></tr></thead>
          <tbody>{estimate.comparaveis.map((row: IntelComparable) => (
            <tr key={row.id}>
              <td>{[row.bairro, row.endereco].filter(Boolean).join(' · ') || 'Não informado'}</td>
              <td>{formatMoney(row.valor)}</td><td>{row.area_m2 ? `${Number(row.area_m2)} m²` : '—'}</td><td>{formatMoney(row.valor_m2 ?? null)}</td>
              <td>{row.tipo_preco === 'TRANSACIONADO' ? 'Transacionado' : 'Anunciado'}</td>
              <td>{row.similaridade == null ? '—' : Number(row.similaridade).toFixed(2)}</td>
              <td>{row.usado ? <Badge size="sm" tone="success">Usado</Badge> : <span title={row.motivo ?? ''}>Excluído: {row.motivo}</span>}</td>
              <td>{row.url ? <a className="market-link" href={row.url} target="_blank" rel="noreferrer">{row.fonte || 'Fonte'} <ExternalLink size={12} /></a> : (row.fonte || '—')}
                {row.consultado_em ? <small> · consultado em {row.consultado_em}</small> : null}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </>
  )
}

function Fact({ label, value }: { label: string; value?: string | null }) {
  return <div><dt>{label}</dt><dd>{value || 'Não informado'}</dd></div>
}
