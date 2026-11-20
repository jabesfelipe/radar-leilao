import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ClipboardCheck, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section, Select, Textarea } from '../components/ui'
import { CHECKLIST_CONFIDENCES, CHECKLIST_STATES, isOpenItem, listChecklist, listChecklistEvidence, sortByPriority, updateChecklistItem, type ChecklistConfidence, type ChecklistEvidence, type ChecklistItem, type ChecklistOutcome, type ChecklistState } from '../services/checklist'

type ChecklistSectionProps = {
  propertyId: number
}

const stateLabels: Record<string, string> = {
  PENDENTE: 'Pendente',
  EM_ANALISE: 'Em análise',
  CONFIRMADO: 'Confirmado',
  RISCO_IDENTIFICADO: 'Risco identificado',
  ATENCAO: 'Atenção',
  NAO_IDENTIFICADO: 'Não identificado',
  NAO_APLICAVEL: 'Não aplicável',
}

const confidenceLabels: Record<string, string> = {
  BAIXA: 'Baixa',
  MEDIA: 'Média',
  ALTA: 'Alta',
}

const stateTone: Record<string, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  PENDENTE: 'neutral',
  EM_ANALISE: 'info',
  CONFIRMADO: 'success',
  RISCO_IDENTIFICADO: 'danger',
  ATENCAO: 'warning',
  NAO_IDENTIFICADO: 'neutral',
  NAO_APLICAVEL: 'neutral',
}

// Resultado para o investidor (v1.0.11): vem pronto do backend; aqui só a ordem e o tom de exibição.
const OUTCOME_ORDER: ChecklistOutcome[] = ['RISCO_IDENTIFICADO', 'PENDENTE', 'INCONCLUSIVO', 'CONFIRMADO', 'SEM_RESTRICAO_IDENTIFICADA', 'NAO_APLICAVEL']

const outcomeTone: Record<ChecklistOutcome, 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  CONFIRMADO: 'success',
  RISCO_IDENTIFICADO: 'danger',
  PENDENTE: 'warning',
  INCONCLUSIVO: 'info',
  NAO_APLICAVEL: 'neutral',
  SEM_RESTRICAO_IDENTIFICADA: 'success',
}

function stateLabel(state: string) {
  return stateLabels[state] ?? state
}

function normalizeState(state: string): ChecklistState {
  return (CHECKLIST_STATES as readonly string[]).includes(state) ? (state as ChecklistState) : 'PENDENTE'
}

function applicabilityLabel(applicable?: boolean | null) {
  if (applicable === true) return 'Aplicável'
  if (applicable === false) return 'Não aplicável'
  return 'Não informado'
}

function normalizeDraftConfidence(confidence?: string | null): ChecklistConfidence | '' {
  return confidence && (CHECKLIST_CONFIDENCES as readonly string[]).includes(confidence) ? (confidence as ChecklistConfidence) : ''
}

export function ChecklistSection({ propertyId }: ChecklistSectionProps) {
  const [items, setItems] = useState<ChecklistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [rowError, setRowError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [draft, setDraft] = useState<{ state: ChecklistState; confidence: ChecklistConfidence | ''; answer: string }>({ state: 'PENDENTE', confidence: '', answer: '' })
  const [evidence, setEvidence] = useState<Record<number, { loading: boolean; error: string; items: ChecklistEvidence[] }>>({})
  const submittingRef = useRef(false)

  const toggleEvidence = async (item: ChecklistItem) => {
    if (evidence[item.id] && !evidence[item.id].loading) {
      setEvidence((current) => {
        const next = { ...current }
        delete next[item.id]
        return next
      })
      return
    }
    setEvidence((current) => ({ ...current, [item.id]: { loading: true, error: '', items: [] } }))
    try {
      const items = await listChecklistEvidence(propertyId, item.id)
      setEvidence((current) => ({ ...current, [item.id]: { loading: false, error: '', items } }))
    } catch (cause) {
      setEvidence((current) => ({ ...current, [item.id]: { loading: false, error: cause instanceof Error ? cause.message : 'Não foi possível carregar as evidências.', items: [] } }))
    }
  }

  const outcomeCounts = OUTCOME_ORDER
    .map((outcome) => ({ outcome, label: items.find((i) => i.resultado === outcome)?.resultado_label ?? outcome, count: items.filter((i) => i.resultado === outcome).length }))
    .filter((entry) => entry.count > 0)

  const loadChecklist = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setItems(await listChecklist(propertyId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o checklist.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadChecklist() }, [loadChecklist])

  const startEditing = (item: ChecklistItem) => {
    setEditingId(item.id)
    setRowError('')
    setSuccessMessage('')
    setDraft({ state: normalizeState(item.state), confidence: normalizeDraftConfidence(item.confidence), answer: item.answer ?? '' })
  }

  const submit = async (event: FormEvent<HTMLFormElement>, item: ChecklistItem) => {
    event.preventDefault()
    if (submittingRef.current) return
    submittingRef.current = true
    setSavingId(item.id)
    setRowError('')
    setSuccessMessage('')
    try {
      const currentConfidence = normalizeDraftConfidence(item.confidence)
      const confidence = draft.confidence || currentConfidence
      const updated = await updateChecklistItem(propertyId, item.id, {
        state: draft.state,
        answer: draft.answer,
        ...(confidence ? { confidence } : {}),
        interpretation: item.interpretation ?? null,
        risk: item.risk ?? null,
      })
      setItems((current) => current.map((entry) => (entry.id === item.id ? { ...entry, ...updated, question: entry.question } : entry)))
      setEditingId(null)
      setSuccessMessage('Item do checklist atualizado com sucesso.')
    } catch (cause) {
      setRowError(cause instanceof Error ? cause.message : 'Não foi possível atualizar o item.')
    } finally {
      setSavingId(null)
      submittingRef.current = false
    }
  }

  return (
    <Section title="Checklist Mestre" description="Itens do Checklist Mestre aplicados a este imóvel." className="dossier-section">
      {successMessage && <Alert tone="success" title="Atualização concluída" className="dossier-feedback">{successMessage}</Alert>}

      {loading ? (
        <LoadingState label="Carregando checklist…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadChecklist()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : items.length === 0 ? (
        <Card padding="none"><EmptyState title="Checklist não disponível" description="Ainda não há itens de checklist para este imóvel." icon={<ClipboardCheck size={24} />} /></Card>
      ) : (
        <div className="checklist-list">
          {outcomeCounts.length > 0 && (
            <Card padding="md" className="checklist-summary" aria-label="Resumo do checklist">
              {outcomeCounts.map((entry) => (
                <Badge key={entry.outcome} tone={outcomeTone[entry.outcome]} size="sm">{`${entry.label}: ${entry.count}`}</Badge>
              ))}
            </Card>
          )}
          {items.some((i) => i.prioridade) && (
            <Card padding="md" className="checklist-summary" aria-label="Pendências por prioridade">
              {(['P0', 'P1', 'P2', 'P3'] as const).map((p) => {
                const open = items.filter((i) => i.prioridade === p && isOpenItem(i))
                return <Badge key={p} tone={p === 'P0' && open.length ? 'danger' : p === 'P1' && open.length ? 'warning' : 'neutral'} size="sm">{`${p}: ${open.length} em aberto`}</Badge>
              })}
              {items.filter((i) => i.prioridade === 'P0' && isOpenItem(i)).length > 0 ? (
                <p className="market-obs">Bloqueadores (P0) em aberto: {items.filter((i) => i.prioridade === 'P0' && isOpenItem(i)).map((i) => i.question).join('; ')}.</p>
              ) : null}
            </Card>
          )}
          {sortByPriority(items).map((item) => {
            const isEditing = editingId === item.id
            const isSaving = savingId === item.id
            const itemEvidence = evidence[item.id]
            const evidenceCount = item.evidence_ids?.length ?? 0
            return (
              <Card key={item.id} padding="lg" className="checklist-item">
                <div className="checklist-item-head">
                  <div className="checklist-item-title">
                    {item.item_number != null && <span className="checklist-number">{String(item.item_number).padStart(2, '0')}</span>}
                    <h3>{item.question}</h3>
                  </div>
                  {item.prioridade_label && <Badge tone={item.prioridade === 'P0' ? 'danger' : item.prioridade === 'P1' ? 'warning' : 'neutral'} size="sm">{item.prioridade_label}</Badge>}
                  {item.resultado && item.resultado_label && (
                    <Badge tone={outcomeTone[item.resultado] ?? 'neutral'} size="sm">{item.resultado_label}</Badge>
                  )}
                  <Badge tone={stateTone[item.state] ?? 'neutral'} size="sm">{stateLabel(item.state)}</Badge>
                </div>

                <dl className="dossier-facts checklist-facts">
                  {item.category && <Fact label="Categoria" value={item.category} />}
                  {item.domain && item.domain.length > 0 && <Fact label="Domínio" value={item.domain.join(', ')} />}
                  {item.origin && <Fact label="Origem" value={item.origin} />}
                  <Fact label="Aplicabilidade" value={applicabilityLabel(item.applicable)} />
                  <Fact label="Confiança" value={item.confidence ? (confidenceLabels[item.confidence] ?? item.confidence) : 'Não informado'} />
                  {item.answer && <Fact label="Conclusão" value={item.answer} />}
                  {item.interpretation && <Fact label="Fundamentação" value={item.interpretation} />}
                  {item.acao_recomendada && <Fact label="O que fazer" value={item.acao_recomendada} />}
                  {item.fonte_necessaria && <Fact label="Fonte necessária" value={item.fonte_necessaria} />}
                  {item.risk && <Fact label="Risco" value={item.risk} />}
                  {item.explicacao && <Fact label="Por que importa" value={item.explicacao} />}
                  {item.proxima_acao && <Fact label="Próxima ação" value={item.proxima_acao} />}
                  {item.responsavel && item.prioridade && <Fact label="Responsável" value={item.responsavel} />}
                </dl>

                {evidenceCount > 0 && (
                  <div className="checklist-evidence">
                    <Button variant="ghost" onClick={() => void toggleEvidence(item)} aria-expanded={Boolean(itemEvidence && !itemEvidence.loading)}>
                      {itemEvidence && !itemEvidence.loading ? 'Ocultar evidências' : `Ver evidências (${evidenceCount})`}
                    </Button>
                    {itemEvidence?.loading && <LoadingState label="Carregando evidências…" />}
                    {itemEvidence?.error && <Alert tone="danger">{itemEvidence.error}</Alert>}
                    {itemEvidence && !itemEvidence.loading && !itemEvidence.error && (
                      <ul className="checklist-evidence-list">
                        {itemEvidence.items.map((ev) => (
                          <li key={ev.id}>
                            <strong>{ev.tipo_evidencia_label ?? ev.tipo_evidencia ?? 'Evidência'}</strong>
                            {ev.fact && <p>{ev.fact}</p>}
                            {ev.source_excerpt && <blockquote>{ev.source_excerpt}</blockquote>}
                            <small>
                              {[ev.documento ? `Documento: ${ev.documento}${ev.version ? ` (v${ev.version})` : ''}` : null,
                                ev.page != null ? `Página ${ev.page}` : ev.section ?? null,
                                ev.agent ? `Responsável: ${ev.agent}` : null,
                                ev.confidence ? `Confiança: ${confidenceLabels[ev.confidence] ?? ev.confidence}` : null,
                                ev.created_at ? `Registrada em ${new Date(ev.created_at).toLocaleDateString('pt-BR')}` : null,
                                `#${ev.id}`].filter(Boolean).join(' · ')}
                            </small>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {isEditing ? (
                  <form className="checklist-form" onSubmit={(event) => submit(event, item)} noValidate>
                    <Select label="Estado" value={draft.state} onChange={(event) => setDraft((d) => ({ ...d, state: event.target.value as ChecklistState }))}>
                      {CHECKLIST_STATES.map((state) => <option key={state} value={state}>{stateLabel(state)}</option>)}
                    </Select>
                    <Select label="Confiança" value={draft.confidence} onChange={(event) => setDraft((d) => ({ ...d, confidence: event.target.value as ChecklistConfidence | '' }))}>
                      <option value="">Não informar</option>
                      {CHECKLIST_CONFIDENCES.map((confidence) => <option key={confidence} value={confidence}>{confidenceLabels[confidence]}</option>)}
                    </Select>
                    <Textarea label="Resposta" value={draft.answer} onChange={(event) => setDraft((d) => ({ ...d, answer: event.target.value }))} className="checklist-form-full" />
                    <div className="checklist-form-actions">
                      {rowError && <Alert tone="danger">{rowError}</Alert>}
                      <Button variant="ghost" type="button" onClick={() => setEditingId(null)} disabled={isSaving}>Cancelar</Button>
                      <Button type="submit" loading={isSaving}>Salvar</Button>
                    </div>
                  </form>
                ) : (
                  <div className="checklist-item-actions">
                    <Button variant="secondary" onClick={() => startEditing(item)}>Atualizar item</Button>
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </Section>
  )
}

function Fact({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value || 'Não informado'}</dd>
    </div>
  )
}
