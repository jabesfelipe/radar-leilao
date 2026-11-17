import { useEffect, useState } from 'react'
import { Lightbulb } from 'lucide-react'
import { Alert, Badge, Button } from '../components/ui'
import { formatMoney, formatPercent, getMarketIntelligence, type MarketIntelligence } from '../services/market'

// Campos do formulário de premissas que podem receber sugestão (valores no formato do formulário: % para percentuais).
export type SuggestibleField = 'valor_venda_estimado' | 'corretagem_pct' | 'tributo_pct' | 'prazo_meses' | 'carregamento_mensal'
export type CurrentValues = Record<SuggestibleField, string>

type Suggestion = { field: SuggestibleField; label: string; value: string; display: string; origem: string }

const asPct = (v: unknown) => {
  const n = Number(v)
  return Number.isFinite(n) ? String(Math.round(n * 10000) / 100) : ''
}

// Sugestões só vêm da inteligência de mercado já calculada (v1.0.8) e das premissas com origem declarada.
// Nada é preenchido sem o clique do usuário; a meta financeira nunca é sugerida (decisão do investidor).
export function buildSuggestions(data: MarketIntelligence): Suggestion[] {
  const out: Suggestion[] = []
  const v = data.valores
  if (v.valor_mercado_estimado != null) {
    out.push({ field: 'valor_venda_estimado', label: 'Valor de venda estimado', value: String(v.valor_mercado_estimado),
      display: formatMoney(v.valor_mercado_estimado), origem: `estimativa de mercado (${data.venda.quantidade_usada} comparáveis, confiança ${data.venda.confianca})` })
  }
  const p = data.premissas || {}
  const corretagem = p['venda.corretagem_pct']
  if (corretagem?.valor != null) out.push({ field: 'corretagem_pct', label: 'Corretagem na venda', value: asPct(corretagem.valor), display: `${asPct(corretagem.valor)}%`, origem: corretagem.origem })
  const ir = p['venda.tributo_ganho_pct']
  if (ir?.valor != null) out.push({ field: 'tributo_pct', label: 'Tributo na venda (base ganho)', value: asPct(ir.valor), display: `${asPct(ir.valor)}%`, origem: ir.origem })
  const prazo = p['venda.prazo_meses']
  if (prazo?.valor != null) out.push({ field: 'prazo_meses', label: 'Prazo da operação', value: String(prazo.valor), display: `${prazo.valor} meses`, origem: prazo.origem })
  const carregamento = data.carregamento_mensal
  if (carregamento?.valor != null) out.push({ field: 'carregamento_mensal', label: 'Carregamento mensal', value: String(carregamento.valor), display: `${formatMoney(carregamento.valor)}/mês`, origem: carregamento.origem || 'origem não informada' })
  return out
}

export function PremisesSuggestions({ propertyId, current, onApply }: { propertyId: number; current: CurrentValues; onApply: (field: SuggestibleField, value: string) => void }) {
  const [data, setData] = useState<MarketIntelligence | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const payload = await getMarketIntelligence(propertyId)
        if (active && payload && payload.valores && payload.venda) setData(payload)
      } catch {
        if (active) setData(null)   // sem inteligência de mercado: o formulário segue manual
      }
    }
    void load()
    return () => { active = false }
  }, [propertyId])

  if (!data) return null
  const suggestions = buildSuggestions(data)
  const v = data.valores
  return (
    <div className="premises-suggestions dossier-form-full" aria-label="Sugestões para as premissas">
      <p className="wizard-subtitle"><Lightbulb size={16} /> Sugestões a partir dos dados existentes (revise antes de salvar)</p>
      {v.valor_mercado_estimado != null ? (
        <p className="market-obs">
          Mercado: {formatMoney(v.valor_mercado_estimado)}
          {v.faixa_venda ? ` (faixa ${formatMoney(v.faixa_venda.min)} a ${formatMoney(v.faixa_venda.max)})` : ''} · confiança <strong>{data.venda.confianca}</strong> ·{' '}
          {data.venda.quantidade_usada} de {data.venda.quantidade_total} comparáveis usados · {data.venda.quantidade_anunciada} com preço ANUNCIADO
          {Number(data.venda.desconto_negociacao) > 0 ? `, convertido em provável negociado com desconto de ${formatPercent(data.venda.desconto_negociacao)}` : ''}.
        </p>
      ) : (
        <Alert tone="warning" title="Sem estimativa de mercado">
          Sem comparáveis suficientes o valor de venda não é sugerido. Sem ele, o resultado e o preço máximo não são calculados: cadastre comparáveis na seção Mercado ou informe o valor manualmente.
        </Alert>
      )}
      {(data.venda.limitacoes ?? []).length > 0 && (
        <ul className="market-intel-reasons">{(data.venda.limitacoes ?? []).map((l) => <li key={l}>{l}</li>)}</ul>
      )}
      {suggestions.length > 0 && (
        <table className="hub-table" aria-label="Sugestões editáveis">
          <thead><tr><th>Premissa</th><th>Sugestão</th><th>Origem</th><th>Valor atual</th><th /></tr></thead>
          <tbody>{suggestions.map((s) => {
            const filled = current[s.field].trim() !== ''
            const same = filled && Number(current[s.field]) === Number(s.value)
            return (
              <tr key={s.field}>
                <td>{s.label}</td><td>{s.display} <Badge size="sm" tone="info">Sugestão</Badge></td><td><small>{s.origem}</small></td>
                <td>{filled ? current[s.field] : 'vazio'}</td>
                <td>{same ? <Badge size="sm" tone="success">Em uso</Badge> : (
                  <Button type="button" variant="secondary" size="sm" onClick={() => onApply(s.field, s.value)}>{filled ? 'Substituir pelo sugerido' : 'Usar sugestão'}</Button>
                )}</td>
              </tr>
            )
          })}</tbody>
        </table>
      )}
      <p className="market-obs">A meta financeira é decisão do investidor: não há sugestão. Sem meta, o preço máximo não é calculado.</p>
    </div>
  )
}
