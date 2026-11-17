import { Badge } from '../components/ui'
import { formatMoney, type CostCompositionItem } from '../services/finance'

// Natureza de cada valor da composição (a mesma do cenário BASE da inteligência de mercado): o investidor separa o que é
// confirmado, o que ele mesmo informou, o que é estimativa, o que é reserva de um custo ainda pendente e o que falta.
const natureInfo: Record<string, { label: string; tone: 'success' | 'info' | 'warning' | 'danger' | 'neutral' }> = {
  CONFIRMADO: { label: 'Confirmado', tone: 'success' },
  PREMISSA_USUARIO: { label: 'Premissa do usuário', tone: 'info' },
  ESTIMADO: { label: 'Estimado', tone: 'info' },
  RESERVA: { label: 'Pendente (reserva)', tone: 'warning' },
  PENDENTE: { label: 'Pendente (fora da soma)', tone: 'danger' },
  NAO_APLICAVEL: { label: 'Não aplicável', tone: 'neutral' },
}

export function CostComposition({ items }: { items: CostCompositionItem[] }) {
  return (
    <table className="hub-table" aria-label="Composição dos custos">
      <caption className="finance-hint">Composição dos custos (a mesma da inteligência de mercado). Custo pendente nunca entra como zero.</caption>
      <thead><tr><th>Item</th><th>Valor</th><th>Natureza</th><th>Origem</th></tr></thead>
      <tbody>
        {items.map((item) => {
          const info = natureInfo[item.natureza] ?? { label: item.natureza, tone: 'neutral' as const }
          return (
            <tr key={item.chave}>
              <td>{item.descricao}</td>
              <td>{item.incluido ? formatMoney(item.valor as number) : 'fora da soma'}</td>
              <td><Badge size="sm" tone={info.tone}>{info.label}</Badge></td>
              <td><small>{item.natureza === 'RESERVA' && item.base_valor ? item.base_valor : item.origem}</small></td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
