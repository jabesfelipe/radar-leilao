import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { AlertTriangle, Building2, FileText, Scale, Wallet, BarChart3, Home, ClipboardCheck, ShieldAlert, BadgeCheck, History } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section } from '../components/ui'
import {
  getDashboard, getPropertiesSummary, getFinancialHub, getJuridicalHub, getRisksHub,
  getVerdictsHub, getMarketHub, getOccupancyHub, getDocumentsHub, getHistoryHub, getChecklistHub,
  formatMoney, formatPercent,
  type DashboardData, type PropertySummary,
} from '../services/hub'

type HubProps = { onOpenProperty: (id: number) => void }

// Wrapper padrão de carregamento/erro/vazio reutilizado por todos os hubs.
function HubState<T>({ load, children, empty }: { load: () => Promise<T>; children: (data: T) => ReactNode; empty?: string }) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const run = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await load()) } catch (c) { setError(c instanceof Error ? c.message : 'Falha ao carregar.') } finally { setLoading(false) }
  }, [load])
  useEffect(() => { void run() }, [run])
  if (loading) return <LoadingState label="Carregando…" />
  if (error) return <Card padding="lg"><Alert tone="danger" title="Não foi possível carregar">{error}</Alert></Card>
  if (data === null) return <EmptyState title={empty ?? 'Sem dados'} description="Nada para exibir ainda." />
  return <>{children(data)}</>
}

function Kpi({ label, value, tone }: { label: string; value: ReactNode; tone?: 'accent' | 'danger' | 'success' }) {
  return (
    <Card padding="lg" className={`hub-kpi hub-kpi-${tone ?? 'default'}`}>
      <span className="hub-kpi-label">{label}</span>
      <strong className="hub-kpi-value">{value}</strong>
    </Card>
  )
}

function vredTone(v?: string | null): 'success' | 'warning' | 'danger' | 'neutral' {
  switch ((v || '').toUpperCase()) {
    case 'FAVORAVEL': return 'success'
    case 'ATENCAO': return 'warning'
    case 'DESFAVORAVEL': return 'danger'
    default: return 'neutral'
  }
}

export function DashboardHub({ onOpenProperty }: HubProps) {
  return (
    <HubState<DashboardData> load={getDashboard}>
      {(d) => (
        <div className="hub">
          <div className="hub-kpis">
            <Kpi label="Imóveis no Radar" value={d.kpis.imoveis} />
            <Kpi label="Em análise" value={d.kpis.em_analise} />
            <Kpi label="Com pendências" value={d.kpis.com_pendencias} tone="accent" />
            <Kpi label="Riscos altos" value={d.kpis.riscos_altos} tone="danger" />
            <Kpi label="Oportunidades" value={d.kpis.oportunidades} tone="success" />
          </div>
          <Section title="Pipeline" description="Estados reais dos imóveis no Radar." className="hub-section">
            <div className="hub-pipeline">
              {Object.entries(d.pipeline).map(([k, v]) => (
                <Card key={k} padding="md" className="hub-pipeline-step"><span>{k.replace(/_/g, ' ')}</span><strong>{v}</strong></Card>
              ))}
            </div>
          </Section>
          <Section title="Alertas" description="Cada alerta leva ao imóvel correspondente." className="hub-section">
            {d.alertas.length === 0 ? (
              <Card padding="lg"><EmptyState title="Sem alertas" description="Nenhum alerta ativo no momento." icon={<AlertTriangle size={22} />} /></Card>
            ) : (
              <div className="hub-alert-list">
                {d.alertas.map((a, i) => (
                  <button key={i} className="hub-alert" type="button" onClick={() => onOpenProperty(a.property_id)}>
                    <Badge tone={a.tipo === 'RISCO_ALTO' ? 'danger' : a.tipo === 'PENDENCIAS' ? 'warning' : 'info'} size="sm">{a.tipo.replace(/_/g, ' ')}</Badge>
                    <strong>{a.titulo}</strong>
                    <span>{a.detalhe}</span>
                  </button>
                ))}
              </div>
            )}
          </Section>
        </div>
      )}
    </HubState>
  )
}

function SummaryTable({ itens, onOpenProperty }: { itens: PropertySummary[]; onOpenProperty: (id: number) => void }) {
  if (itens.length === 0) return <Card padding="lg"><EmptyState title="Nenhum imóvel" description="Cadastre imóveis para ver os indicadores." icon={<Building2 size={22} />} /></Card>
  return (
    <div className="hub-table-wrap">
      <table className="hub-table">
        <thead><tr><th>Imóvel</th><th>Cidade/UF</th><th>Lance</th><th>Preço máx.</th><th>TCO</th><th>Break-even</th><th>ROI</th><th>Risco</th><th>Veredito</th></tr></thead>
        <tbody>
          {itens.map((r) => (
            <tr key={r.id} className="hub-row" onClick={() => onOpenProperty(r.id)}>
              <td>{r.titulo}</td>
              <td>{[r.cidade, r.uf].filter(Boolean).join('/') || '—'}</td>
              <td>{formatMoney(r.lance)}</td>
              <td>{formatMoney(r.preco_maximo)}{r.preco_maximo_provisorio ? <Badge tone="warning" size="sm">prov.</Badge> : null}</td>
              <td>{formatMoney(r.custo_total)}</td>
              <td>{formatMoney(r.break_even)}</td>
              <td>{formatPercent(r.roi_operacao)}</td>
              <td>{r.risco_alto ? <Badge tone="danger" size="sm">Alto</Badge> : <Badge tone="neutral" size="sm">{r.riscos_ativos ?? 0}</Badge>}</td>
              <td><Badge tone={vredTone(r.veredito)} size="sm">{r.veredito ?? '—'}</Badge></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function FinancialHub({ onOpenProperty }: HubProps) {
  return <HubState load={getFinancialHub}>{(d) => <SummaryTable itens={d.itens} onOpenProperty={onOpenProperty} />}</HubState>
}

export function PropertiesSummaryHub({ onOpenProperty }: HubProps) {
  return <HubState load={getPropertiesSummary}>{(itens) => <SummaryTable itens={itens} onOpenProperty={onOpenProperty} />}</HubState>
}

export function JuridicalHub({ onOpenProperty }: HubProps) {
  return (
    <HubState load={getJuridicalHub}>
      {(d) => (
        <div className="hub">
          <div className="hub-kpis">
            <Kpi label="Processos" value={d.total_processos} />
            <Kpi label="Riscos jurídicos" value={d.riscos_juridicos} tone="danger" />
          </div>
          {d.processos.length === 0 ? <Card padding="lg"><EmptyState title="Nenhum processo" description="Pesquise processos no dossiê de um imóvel." icon={<Scale size={22} />} /></Card> : (
            <div className="hub-table-wrap"><table className="hub-table">
              <thead><tr><th>Imóvel</th><th>Processo</th><th>Tribunal</th><th>Correlação</th><th>Vínculo</th><th>Status</th></tr></thead>
              <tbody>{d.processos.map((p, i) => (
                <tr key={i} className="hub-row" onClick={() => onOpenProperty(Number(p.property_id))}>
                  <td>{String(p.imovel ?? '—')}</td><td>{String(p.numero ?? '—')}</td><td>{String(p.tribunal ?? '—')}</td>
                  <td><Badge tone={(p.correlacao === 'ALTA') ? 'danger' : (p.correlacao === 'MEDIA') ? 'warning' : 'neutral'} size="sm">{String(p.correlacao ?? 'NÃO CONFIRMADA')}</Badge></td>
                  <td>{String(p.vinculo ?? '—')}</td><td>{String(p.status ?? '—')}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )}
        </div>
      )}
    </HubState>
  )
}

export function RisksHub({ onOpenProperty }: HubProps) {
  const [severity, setSeverity] = useState<string>('')
  return (
    <div className="hub">
      <div className="hub-filters">
        {['', 'CRITICA', 'ALTA', 'MEDIA', 'BAIXA'].map((s) => (
          <Button key={s || 'todos'} size="sm" variant={severity === s ? 'primary' : 'ghost'} onClick={() => setSeverity(s)}>{s || 'Todos'}</Button>
        ))}
      </div>
      <HubState key={severity} load={() => getRisksHub(severity || undefined)}>
        {(d) => d.riscos.length === 0 ? <Card padding="lg"><EmptyState title="Nenhum risco" description="Sem riscos ativos para o filtro." icon={<ShieldAlert size={22} />} /></Card> : (
          <div className="hub-table-wrap"><table className="hub-table">
            <thead><tr><th>Imóvel</th><th>Domínio</th><th>Severidade</th><th>Descrição</th><th>Origem</th><th>Versão</th></tr></thead>
            <tbody>{d.riscos.map((r) => (
              <tr key={String(r.id)} className="hub-row" onClick={() => onOpenProperty(Number(r.property_id))}>
                <td>{String(r.imovel ?? '—')}</td><td>{String(r.dominio ?? '—')}</td>
                <td><Badge tone={(r.severidade === 'CRITICA' || r.severidade === 'ALTA') ? 'danger' : (r.severidade === 'MEDIA') ? 'warning' : 'neutral'} size="sm">{String(r.severidade ?? '—')}</Badge></td>
                <td>{String(r.descricao ?? '—')}</td><td>{String(r.origem ?? '—')}</td><td>{String(r.analysis_version ?? '—')}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </HubState>
    </div>
  )
}

export function VerdictsHub({ onOpenProperty }: HubProps) {
  return (
    <HubState load={getVerdictsHub}>
      {(d) => d.vereditos.length === 0 ? <Card padding="lg"><EmptyState title="Nenhum veredito" description="Execute análises para ver vereditos." icon={<BadgeCheck size={22} />} /></Card> : (
        <div className="hub-table-wrap"><table className="hub-table">
          <thead><tr><th>Imóvel</th><th>Veredito</th><th>Preço máx.</th><th>TCO</th><th>ROI</th><th>Pendências</th><th>Versão</th></tr></thead>
          <tbody>{d.vereditos.map((v) => (
            <tr key={String(v.property_id)} className="hub-row" onClick={() => onOpenProperty(Number(v.property_id))}>
              <td>{String(v.imovel ?? '—')}</td><td><Badge tone={vredTone(String(v.veredito))} size="sm">{String(v.veredito ?? '—')}</Badge></td>
              <td>{formatMoney(v.preco_maximo as number)}</td><td>{formatMoney(v.custo_total as number)}</td>
              <td>{formatPercent(v.roi_operacao as number)}</td><td>{String(v.pendencias ?? 0)}</td><td>{String(v.analysis_version ?? '—')}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </HubState>
  )
}

export function MarketHub({ onOpenProperty }: HubProps) {
  return (
    <HubState load={getMarketHub}>
      {(d) => d.comparaveis.length === 0 ? <Card padding="lg"><EmptyState title="Sem comparáveis" description="Cadastre comparáveis no dossiê." icon={<BarChart3 size={22} />} /></Card> : (
        <div className="hub-table-wrap"><table className="hub-table">
          <thead><tr><th>Imóvel</th><th>Tipo</th><th>Preço</th><th>Aluguel</th><th>Área</th><th>Fonte</th></tr></thead>
          <tbody>{d.comparaveis.map((c, i) => (
            <tr key={i} className="hub-row" onClick={() => onOpenProperty(Number(c.property_id))}>
              <td>{String(c.imovel ?? '—')}</td><td>{String(c.tipo ?? '—')}</td><td>{formatMoney(c.preco as number)}</td>
              <td>{formatMoney(c.aluguel as number)}</td><td>{String(c.area_m2 ?? '—')}</td><td>{String(c.fonte ?? '—')}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </HubState>
  )
}

export function OccupancyHub({ onOpenProperty }: HubProps) {
  return (
    <HubState load={getOccupancyHub}>
      {(d) => d.ocupacoes.length === 0 ? <Card padding="lg"><EmptyState title="Sem ocupação" description="Registre a ocupação no dossiê." icon={<Home size={22} />} /></Card> : (
        <div className="hub-table-wrap"><table className="hub-table">
          <thead><tr><th>Imóvel</th><th>Status</th><th>Perfil</th><th>Custo estimado</th><th>Meses</th></tr></thead>
          <tbody>{d.ocupacoes.map((o) => (
            <tr key={String(o.property_id)} className="hub-row" onClick={() => onOpenProperty(Number(o.property_id))}>
              <td>{String(o.imovel ?? '—')}</td><td><Badge tone={(o.status === 'OCUPADO') ? 'warning' : (o.status === 'DESOCUPADO') ? 'success' : 'neutral'} size="sm">{String(o.status ?? '—')}</Badge></td>
              <td>{String(o.perfil ?? '—')}</td><td>{formatMoney(o.custo_estimado as number)}</td><td>{String(o.meses_estimados ?? '—')}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </HubState>
  )
}

export function ChecklistHub({ onOpenProperty }: HubProps) {
  return (
    <HubState load={getChecklistHub}>
      {(d) => (
        <div className="hub">
          <div className="hub-kpis">
            <Kpi label="Confirmados" value={d.totais.CONFIRMADO ?? 0} tone="success" />
            <Kpi label="Pendentes" value={(d.totais.PENDENTE ?? 0) + (d.totais.EM_ANALISE ?? 0)} tone="accent" />
            <Kpi label="Atenção" value={(d.totais.ATENCAO ?? 0) + (d.totais.RISCO_IDENTIFICADO ?? 0)} tone="danger" />
          </div>
          {d.itens.length === 0 ? <Card padding="lg"><EmptyState title="Sem checklist" description="Cadastre imóveis para ver o checklist." icon={<ClipboardCheck size={22} />} /></Card> : (
            <div className="hub-table-wrap"><table className="hub-table">
              <thead><tr><th>Imóvel</th><th>Confirmados</th><th>Pendentes</th><th>Atenção</th></tr></thead>
              <tbody>{d.itens.map((it) => (
                <tr key={String(it.property_id)} className="hub-row" onClick={() => onOpenProperty(Number(it.property_id))}>
                  <td>{String(it.imovel ?? '—')}</td><td>{String(it.confirmados ?? 0)}</td><td>{String(it.pendentes ?? 0)}</td><td>{String(it.atencao ?? 0)}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )}
        </div>
      )}
    </HubState>
  )
}

export function DocumentsHub({ onOpenProperty }: HubProps) {
  const [tipo, setTipo] = useState('')
  return (
    <div className="hub">
      <div className="hub-filters">
        {['', 'Edital', 'Matrícula', 'Jurídico', 'Financeiro', 'Outro'].map((t) => (
          <Button key={t || 'todos'} size="sm" variant={tipo === t ? 'primary' : 'ghost'} onClick={() => setTipo(t)}>{t || 'Todos'}</Button>
        ))}
      </div>
      <HubState key={tipo} load={() => getDocumentsHub(tipo || undefined)}>
        {(d) => d.documentos.length === 0 ? <Card padding="lg"><EmptyState title="Nenhum documento" description="Faça upload no dossiê de um imóvel." icon={<FileText size={22} />} /></Card> : (
          <div className="hub-table-wrap"><table className="hub-table">
            <thead><tr><th>Documento</th><th>Imóvel</th><th>Tipo</th><th>Versão</th><th>Origem</th><th>Status</th></tr></thead>
            <tbody>{d.documentos.map((doc) => (
              <tr key={String(doc.id)} className="hub-row" onClick={() => onOpenProperty(Number(doc.property_id))}>
                <td>{String(doc.nome ?? '—')}</td><td>{String(doc.imovel ?? '—')}</td><td>{String(doc.tipo ?? '—')}</td>
                <td>{String(doc.versao ?? '—')}</td><td>{String(doc.origem ?? '—')}</td><td>{String(doc.status ?? '—')}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </HubState>
    </div>
  )
}

export function HistoryHub({ onOpenProperty }: HubProps) {
  return (
    <HubState load={getHistoryHub}>
      {(d) => d.eventos.length === 0 ? <Card padding="lg"><EmptyState title="Sem histórico" description="As ações aparecerão aqui." icon={<History size={22} />} /></Card> : (
        <div className="hub-timeline">
          {d.eventos.map((e) => (
            <button key={String(e.id)} type="button" className="hub-timeline-item" onClick={() => e.property_id && onOpenProperty(Number(e.property_id))}>
              <span className="hub-timeline-dot" />
              <div>
                <strong>{String(e.evento ?? '—')}</strong>
                <span>{String(e.imovel ?? '—')} · {String(e.entidade ?? '')}</span>
              </div>
              <time>{e.created_at ? new Date(String(e.created_at)).toLocaleString('pt-BR') : ''}</time>
            </button>
          ))}
        </div>
      )}
    </HubState>
  )
}
