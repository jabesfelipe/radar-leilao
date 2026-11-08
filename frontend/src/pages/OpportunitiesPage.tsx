import { useCallback, useEffect, useState } from 'react'
import { GitBranch, RefreshCw, ShieldAlert } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import {
  listOpportunities, listModalities, createOpportunity, getOpportunity, getTransitions,
  getHardStops, getHistory, requestTransition, correctModality, setPhaseState,
  type OpportunityRow, type Modality, type PhaseEvaluation, type TransitionDecision,
  type HardStop, type TransitionRow,
} from '../services/opportunities'

const PHASE_TONE: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {}

export function OpportunitiesPage() {
  const [rows, setRows] = useState<OpportunityRow[]>([])
  const [modalities, setModalities] = useState<Modality[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<number | null>(null)
  const [fModality, setFModality] = useState('')
  const [fStatus, setFStatus] = useState('')
  const [newPropId, setNewPropId] = useState('')
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [opps, mods] = await Promise.all([
        listOpportunities({ modality: fModality || undefined, status: fStatus || undefined }),
        listModalities(),
      ])
      setRows(opps.itens); setModalities(mods.modalidades)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Falha ao carregar oportunidades.')
    } finally {
      setLoading(false)
    }
  }, [fModality, fStatus])

  useEffect(() => { void load() }, [load])

  const create = async () => {
    setMsg('')
    try {
      const out = await createOpportunity({ property_id: Number(newPropId) })
      setNewPropId(''); setMsg(`Oportunidade #${out.oportunidade.id} criada.`); await load()
      setSelected(out.oportunidade.id)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Falha ao criar.') }
  }

  return (
    <Section title="Oportunidades" description="Ciclo de vida F0–F13 por oportunidade: fase, hard stops, transições e histórico. Regras validadas no backend.">
      {error && <Alert tone="danger">{error}</Alert>}
      {msg && <Alert tone="success">{msg}</Alert>}

      <Card padding="md" className="admin-form">
        <div className="opp-filters">
          <label className="admin-field">Modalidade
            <select value={fModality} onChange={(e) => setFModality(e.target.value)}>
              <option value="">Todas</option>
              {modalities.map((m) => <option key={m.code} value={m.code}>{m.code}</option>)}
            </select>
          </label>
          <label className="admin-field">Status
            <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
              <option value="">Todos</option>
              {['EM_PROSPECCAO', 'EM_ANALISE', 'EM_DECISAO', 'APROVADA', 'ADQUIRIDA', 'ENCERRADA', 'DESCARTADA', 'PERDIDA'].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <Input label="Criar p/ imóvel (ID)" value={newPropId} onChange={(e) => setNewPropId(e.target.value)} />
          <Button onClick={create} disabled={!newPropId}>Criar oportunidade</Button>
        </div>
      </Card>

      {loading ? (
        <LoadingState label="Carregando oportunidades..." />
      ) : rows.length === 0 ? (
        <EmptyState title="Sem oportunidades" description="Crie uma oportunidade a partir de um imóvel." icon={<GitBranch size={22} />} />
      ) : (
        <table className="admin-table">
          <thead><tr><th>#</th><th>Imóvel</th><th>Município</th><th>Modalidade</th><th>Fase</th><th>Status</th><th>Bloqueada</th><th></th></tr></thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.id}>
                <td>{o.id}</td><td>#{o.property_id}</td><td>{o.municipio ?? '—'}</td>
                <td>{o.modality}</td><td>{o.current_phase}</td><td>{o.status}</td>
                <td><Badge tone={o.blocked ? 'danger' : 'success'}>{o.blocked ? 'Sim' : 'Não'}</Badge></td>
                <td className="admin-row-actions"><Button variant="ghost" onClick={() => setSelected(o.id)}>Abrir</Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected != null && <OpportunityDetail id={selected} modalities={modalities} onChanged={load} onClose={() => setSelected(null)} />}
    </Section>
  )
}

function OpportunityDetail({ id, modalities, onChanged, onClose }: { id: number; modalities: Modality[]; onChanged: () => void; onClose: () => void }) {
  const [fase, setFase] = useState<PhaseEvaluation | null>(null)
  const [transitions, setTransitions] = useState<TransitionDecision[]>([])
  const [stops, setStops] = useState<HardStop[]>([])
  const [history, setHistory] = useState<TransitionRow[]>([])
  const [modality, setModality] = useState('')
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(''); const [ok, setOk] = useState(''); const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setErr('')
    try {
      const [detail, tr, hs, hist] = await Promise.all([getOpportunity(id), getTransitions(id), getHardStops(id), getHistory(id)])
      setFase(detail.fase); setModality(detail.oportunidade.modality)
      setTransitions(tr.transicoes); setStops(hs.hard_stops); setHistory(hist.historico)
    } catch (cause) { setErr(cause instanceof Error ? cause.message : 'Falha ao carregar detalhe.') }
    finally { setLoading(false) }
  }, [id])

  useEffect(() => { void load() }, [load])

  const doTransition = async (target: string, type: string, decision?: string) => {
    setBusy(true); setErr(''); setOk('')
    try {
      const justification = type === 'DESCARTE' ? (window.prompt('Justificativa do descarte:') || '') : undefined
      const out = await requestTransition(id, { target_phase: target, transition_type: type, justification, decision })
      setOk(out.decision.allowed ? `Transição aplicada: ${out.decision.from_phase} → ${out.decision.to_phase}.` : `Bloqueada: ${out.decision.reason}`)
      await load(); onChanged()
    } catch (cause) { setErr(cause instanceof Error ? cause.message : 'Falha na transição.') }
    finally { setBusy(false) }
  }

  const concludePhase = async () => {
    setBusy(true); setErr(''); setOk('')
    try {
      await setPhaseState(id, { state: 'CONCLUIDA' })
      setOk('Fase concluída. Avanço habilitado se não houver hard stop ativo.'); await load(); onChanged()
    } catch (cause) { setErr(cause instanceof Error ? cause.message : 'Falha ao concluir fase.') }
    finally { setBusy(false) }
  }

  const applyModality = async () => {
    setBusy(true); setErr(''); setOk('')
    try {
      await correctModality(id, { modality, justification: 'Correção manual via UI' })
      setOk('Modalidade atualizada.'); await load(); onChanged()
    } catch (cause) { setErr(cause instanceof Error ? cause.message : 'Falha ao corrigir modalidade.') }
    finally { setBusy(false) }
  }

  return (
    <Card padding="lg" className="opp-detail">
      <div className="admin-row-actions" style={{ justifyContent: 'space-between' }}>
        <p className="admin-form-title">Oportunidade #{id}</p>
        <Button variant="ghost" onClick={onClose}>Fechar</Button>
      </div>
      {loading ? <LoadingState label="Carregando..." /> : (
        <>
          {err && <Alert tone="danger">{err}</Alert>}
          {ok && <Alert tone="success">{ok}</Alert>}
          {fase && (
            <Card padding="md" className="market-quality">
              <dl className="dossier-facts">
                <div><dt>Fase atual</dt><dd>{fase.phase}</dd></div>
                <div><dt>Estado</dt><dd>{fase.phase_state}</dd></div>
                <div><dt>Gate satisfeito</dt><dd>{fase.gate_satisfied ? 'Sim' : 'Não'}</dd></div>
                <div><dt>Bloqueado</dt><dd><Badge tone={fase.blocked ? 'danger' : 'success'}>{fase.blocked ? 'Sim' : 'Não'}</Badge></dd></div>
              </dl>
              <p className="market-obs">Próxima ação: {fase.next_action}</p>
              {!fase.gate_satisfied && !fase.blocked && (
                <Button variant="ghost" onClick={concludePhase} disabled={busy}>
                  <RefreshCw size={14} /> Concluir fase atual (satisfaz gate)
                </Button>
              )}
            </Card>
          )}

          <label className="admin-field">Modalidade
            <select value={modality} onChange={(e) => setModality(e.target.value)}>
              {modalities.map((m) => <option key={m.code} value={m.code}>{m.code}</option>)}
            </select>
          </label>
          <Button variant="ghost" onClick={applyModality} disabled={busy}>Corrigir modalidade</Button>

          <p className="admin-form-title">Hard stops ({stops.length})</p>
          {stops.length === 0 ? <p className="wizard-muted">Nenhum hard stop ativo.</p> : stops.map((s) => (
            <Alert key={s.code} tone="danger"><ShieldAlert size={14} /> <strong>{s.code}</strong> — {s.description} ({s.acao_necessaria})</Alert>
          ))}

          <p className="admin-form-title">Transições disponíveis</p>
          <div className="admin-row-actions">
            {transitions.map((t) => (
              <Button key={`${t.transition_type}-${t.to_phase}`} variant={t.allowed ? 'primary' : 'ghost'} disabled={!t.allowed || busy}
                onClick={() => doTransition(t.to_phase, t.transition_type || 'AVANCO')} title={t.reason}>
                {t.transition_type} → {t.to_phase}{t.allowed ? '' : ' (bloqueada)'}
              </Button>
            ))}
          </div>

          <p className="admin-form-title">Histórico ({history.length})</p>
          {history.length === 0 ? <p className="wizard-muted">Sem transições.</p> : (
            <table className="admin-table">
              <thead><tr><th>#</th><th>De</th><th>Para</th><th>Tipo</th><th>Resultado</th><th>Ator</th></tr></thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id}><td>{h.id}</td><td>{h.from_phase ?? '—'}</td><td>{h.to_phase}</td><td>{h.transition_type}</td>
                    <td><Badge tone={h.result === 'PERMITIDA' ? 'success' : 'danger'}>{h.result}</Badge></td><td>{h.actor}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </Card>
  )
}
