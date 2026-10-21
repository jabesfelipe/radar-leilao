import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { ExternalLink, MapPin, Plus, RefreshCw, ShieldCheck } from 'lucide-react'
import { Alert, Badge, Button, Card, LoadingState, Section, Select } from '../components/ui'
import {
  addPrefeituraDebt, geocodeLocation, getDueDiligence, reviewFront, updateLocation,
  type DueDiligenceOverview, type FrontSummary,
} from '../services/dueDiligence'

type Props = { propertyId: number }

const RATINGS = ['NAO_VERIFICADO', 'BOM', 'REGULAR', 'RUIM']

// Tom visual por estado da frente (distingue consultado/negativo/não consultado/etc).
const statusTone: Record<string, 'neutral' | 'warning' | 'success' | 'danger' | 'info'> = {
  CONSULTADO: 'success',
  SEM_OCORRENCIA: 'info',
  NAO_INICIADO: 'neutral',
  NAO_CONFIGURADO: 'neutral',
  AGUARDANDO_ACAO: 'warning',
  EM_EXECUCAO: 'warning',
  CONCLUIDO_COM_PENDENCIAS: 'warning',
  NECESSITA_REVISAO: 'warning',
  INDISPONIVEL: 'warning',
  FALHOU: 'danger',
}

const statusLabel: Record<string, string> = {
  CONSULTADO: 'Consultado',
  SEM_OCORRENCIA: 'Sem ocorrência encontrada',
  NAO_INICIADO: 'Não consultado',
  NAO_CONFIGURADO: 'Integração não configurada',
  AGUARDANDO_ACAO: 'Aguardando ação',
  EM_EXECUCAO: 'Em execução',
  CONCLUIDO_COM_PENDENCIAS: 'Concluído com pendências',
  NECESSITA_REVISAO: 'Necessita revisão',
  INDISPONIVEL: 'Consulta indisponível',
  FALHOU: 'Falhou',
}

function money(value: number | string | null | undefined) {
  if (value === undefined || value === null || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n)
}

export function DueDiligenceSection({ propertyId }: Props) {
  const [data, setData] = useState<DueDiligenceOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)
  const [debtOpen, setDebtOpen] = useState(false)
  const [debtForm, setDebtForm] = useState({ category: 'IPTU', amount: '', reference_date: '', status: 'INFORMADO', source: '' })

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await getDueDiligence(propertyId)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Não foi possível carregar a due diligence.') }
    finally { setLoading(false) }
  }, [propertyId])

  useEffect(() => { void load() }, [load])

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true); setActionError('')
    try { await fn(); await load(); return true }
    catch (cause) { setActionError(cause instanceof Error ? cause.message : 'Não foi possível concluir a operação.'); return false }
    finally { setBusy(false) }
  }

  if (loading) return <Section title="Due Diligence" className="dossier-section"><LoadingState label="Carregando due diligence…" /></Section>
  if (error || !data) {
    return (
      <Section title="Due Diligence" className="dossier-section">
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error || 'Sem dados.'}</Alert>
          <Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      </Section>
    )
  }

  const loc = data.localizacao
  const f = data.frentes

  const submitDebt = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const ok = await run(() => addPrefeituraDebt(propertyId, {
      category: debtForm.category.trim() || 'IPTU',
      amount: debtForm.amount.trim() ? Number(debtForm.amount) : 0,
      reference_date: debtForm.reference_date.trim() || undefined,
      status: debtForm.status,
      source: debtForm.source.trim() || undefined,
    }))
    if (ok) { setDebtOpen(false); setDebtForm({ category: 'IPTU', amount: '', reference_date: '', status: 'INFORMADO', source: '' }) }
  }

  const setRating = (key: string, rating: string) => {
    const checklist: Record<string, string> = {}
    for (const item of loc.location_checklist) checklist[item.key] = item.rating
    checklist[key] = rating
    void run(() => updateLocation(propertyId, { location_checklist: checklist }))
  }

  return (
    <Section title="Due Diligence" description="Investigação integrada: matrícula/ônus, processos judiciais, prefeitura/IPTU e localização. Ausência de resultado não é prova de ausência de risco." className="dossier-section">
      {actionError && <Alert tone="danger" title="Falha na operação" className="dossier-feedback">{actionError}</Alert>}

      <div className="finance-list">
        <FrontCard title="Matrícula e ônus" front={f.MATRICULA} busy={busy} onReview={(r) => void run(() => reviewFront(propertyId, 'MATRICULA', { reviewed: r, reviewed_by: 'usuário' }))}>
          <div className="wizard-muted">Titular: {f.MATRICULA.titular || 'Não confirmado'} · Matrícula: {f.MATRICULA.matricula || '—'}</div>
          <div className="wizard-muted">Importe a matrícula atualizada em Documentos; a extração estruturada alimenta esta frente.</div>
        </FrontCard>

        <FrontCard title="Processos judiciais" front={f.JUDICIAL} busy={busy} onReview={(r) => void run(() => reviewFront(propertyId, 'JUDICIAL', { reviewed: r, reviewed_by: 'usuário' }))}>
          <div className="wizard-muted">Processos: {f.JUDICIAL.processos ?? 0} · Relevantes: {f.JUDICIAL.relevantes ?? 0} · Possíveis homônimos: {f.JUDICIAL.homonimos ?? 0}</div>
          <div className="wizard-muted">Consulta e correlação na aba Processos Jurídicos (reutiliza a Judicial API).</div>
        </FrontCard>

        <FrontCard title="Prefeitura e IPTU" front={f.PREFEITURA} busy={busy} onReview={(r) => void run(() => reviewFront(propertyId, 'PREFEITURA', { reviewed: r, reviewed_by: 'usuário' }))}>
          <div className="wizard-muted">Débitos municipais: {f.PREFEITURA.debitos_municipais ?? 0} · Em aberto: {money(f.PREFEITURA.total_em_aberto)}</div>
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => setDebtOpen((v) => !v)}><Plus size={14} /> Registrar débito (consulta manual)</Button>
          {debtOpen && (
            <form className="dossier-form" onSubmit={submitDebt} noValidate>
              <Select label="Categoria" value={debtForm.category} onChange={(e) => setDebtForm((c) => ({ ...c, category: e.target.value }))}>
                {['IPTU', 'TAXA', 'CONDOMINIO', 'OUTROS'].map((o) => <option key={o} value={o}>{o}</option>)}
              </Select>
              <label className="field"><span>Valor</span><input type="number" step="0.01" value={debtForm.amount} onChange={(e) => setDebtForm((c) => ({ ...c, amount: e.target.value }))} /></label>
              <label className="field"><span>Data-base/exercício</span><input type="date" value={debtForm.reference_date} onChange={(e) => setDebtForm((c) => ({ ...c, reference_date: e.target.value }))} /></label>
              <Select label="Situação" value={debtForm.status} onChange={(e) => setDebtForm((c) => ({ ...c, status: e.target.value }))}>
                {['INFORMADO', 'ESTIMADO', 'CONFIRMADO', 'CONTESTADO', 'PAGO', 'CANCELADO', 'PENDENTE'].map((o) => <option key={o} value={o}>{o}</option>)}
              </Select>
              <label className="field"><span>Fonte</span><input value={debtForm.source} onChange={(e) => setDebtForm((c) => ({ ...c, source: e.target.value }))} /></label>
              <div className="dossier-form-actions">
                <Button variant="ghost" type="button" onClick={() => setDebtOpen(false)} disabled={busy}>Cancelar</Button>
                <Button type="submit" loading={busy}>Salvar débito</Button>
              </div>
            </form>
          )}
        </FrontCard>

        <FrontCard title="Localização e entorno" front={f.LOCALIZACAO} busy={busy} onReview={(r) => void run(() => reviewFront(propertyId, 'LOCALIZACAO', { reviewed: r, reviewed_by: 'usuário' }))}>
          <div className="wizard-muted">{loc.endereco}</div>
          <div className="wizard-muted">
            Integração Google Maps: <strong>{loc.integracao_maps === 'CONFIGURADO' ? 'configurada' : 'não configurada'}</strong>
            {loc.latitude != null && loc.longitude != null ? ` · ${loc.latitude}, ${loc.longitude} (${loc.geocode_precision || '—'})` : ' · sem coordenadas'}
          </div>
          <div className="dossier-form-actions" style={{ gap: 8, flexWrap: 'wrap' }}>
            {loc.integracao_maps === 'CONFIGURADO' && (
              <Button size="sm" variant="secondary" disabled={busy} onClick={() => void run(() => geocodeLocation(propertyId))}><MapPin size={14} /> Geocodificar</Button>
            )}
            {loc.maps_url && <a className="link-button" href={loc.maps_url} target="_blank" rel="noreferrer"><ExternalLink size={14} /> Abrir no Google Maps</a>}
            {loc.street_view_url && <a className="link-button" href={loc.street_view_url} target="_blank" rel="noreferrer"><ExternalLink size={14} /> Street View</a>}
            {loc.latitude != null && (
              <Button size="sm" variant="ghost" disabled={busy} onClick={() => void run(() => updateLocation(propertyId, { coordinates_confirmed: !loc.coordinates_confirmed }))}>
                <ShieldCheck size={14} /> {loc.coordinates_confirmed ? 'Ponto confirmado' : 'Confirmar que o ponto é a unidade'}
              </Button>
            )}
          </div>
          <div className="dd-checklist">
            <p className="eyebrow">CHECKLIST DE LOCALIZAÇÃO</p>
            {loc.location_checklist.map((item) => (
              <div key={item.key} className="dd-checklist-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <span>{item.label}</span>
                <Select aria-label={item.label} value={item.rating} disabled={busy} onChange={(e) => setRating(item.key, e.target.value)}>
                  {RATINGS.map((r) => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                </Select>
              </div>
            ))}
            <p className="finance-hint">A avaliação se limita a características observáveis do local; não se infere perfil socioeconômico das pessoas nem a condição interna do imóvel a partir da fachada.</p>
          </div>
        </FrontCard>
      </div>
    </Section>
  )
}

function FrontCard({ title, front, busy, onReview, children }: { title: string; front: FrontSummary; busy: boolean; onReview: (reviewed: boolean) => void; children?: React.ReactNode }) {
  return (
    <Card padding="lg" className="finance-card dd-front-card">
      <div className="dossier-current-head">
        <div><p className="eyebrow">{title}</p></div>
        <Badge tone={statusTone[front.status] ?? 'neutral'} size="sm">{statusLabel[front.status] ?? front.status}</Badge>
      </div>
      {front.integracao && front.integracao !== 'CONFIGURADO' && (
        <Alert tone="info" title="Integração não configurada">A consulta automática desta fonte exige configuração/credencial. Use a importação/consulta manual.</Alert>
      )}
      {children}
      {Array.isArray(front.pendencias) && front.pendencias.length > 0 && (
        <div className="finance-pendencias">
          <strong>Pendências</strong>
          <ul>{front.pendencias.map((p, i) => <li key={i}>{p}</li>)}</ul>
        </div>
      )}
      <div className="dossier-form-actions">
        <span className="wizard-muted">{front.ultima_consulta ? `Última consulta: ${new Date(front.ultima_consulta).toLocaleString('pt-BR')}` : 'Nunca consultado'}</span>
        <Button size="sm" variant="ghost" disabled={busy} onClick={() => onReview(!front.revisado)}>
          {front.revisado ? 'Revisado ✓' : 'Marcar como revisado'}
        </Button>
      </div>
    </Card>
  )
}
