import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ClipboardCheck, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, LoadingState, Section, Select, Textarea } from '../components/ui'
import { CHECKLIST_CONFIDENCES, CHECKLIST_STATES, listChecklist, updateChecklistItem, type ChecklistConfidence, type ChecklistItem, type ChecklistState } from '../services/checklist'

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

function stateLabel(state: string) {
  return stateLabels[state] ?? state
}

function normalizeState(state: string): ChecklistState {
  return (CHECKLIST_STATES as readonly string[]).includes(state) ? (state as ChecklistState) : 'PENDENTE'
}

function normalizeConfidence(confidence?: string | null): ChecklistConfidence {
  return confidence && (CHECKLIST_CONFIDENCES as readonly string[]).includes(confidence) ? (confidence as ChecklistConfidence) : 'MEDIA'
}

export function ChecklistSection({ propertyId }: ChecklistSectionProps) {
  const [items, setItems] = useState<ChecklistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [rowError, setRowError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [draft, setDraft] = useState<{ state: ChecklistState; confidence: ChecklistConfidence; answer: string }>({ state: 'PENDENTE', confidence: 'MEDIA', answer: '' })
  const submittingRef = useRef(false)

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
    setDraft({ state: normalizeState(item.state), confidence: normalizeConfidence(item.confidence), answer: item.answer ?? '' })
  }

  const submit = async (event: FormEvent<HTMLFormElement>, item: ChecklistItem) => {
    event.preventDefault()
    if (submittingRef.current) return
    submittingRef.current = true
    setSavingId(item.id)
    setRowError('')
    setSuccessMessage('')
    try {
      const updated = await updateChecklistItem(propertyId, item.id, {
        state: draft.state,
        answer: draft.answer,
        confidence: draft.confidence,
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
          {items.map((item) => {
            const isEditing = editingId === item.id
            const isSaving = savingId === item.id
            return (
              <Card key={item.id} padding="lg" className="checklist-item">
                <div className="checklist-item-head">
                  <div className="checklist-item-title">
                    {item.item_number != null && <span className="checklist-number">{String(item.item_number).padStart(2, '0')}</span>}
                    <h3>{item.question}</h3>
                  </div>
                  <Badge tone={stateTone[item.state] ?? 'neutral'} size="sm">{stateLabel(item.state)}</Badge>
                </div>

                <dl className="dossier-facts checklist-facts">
                  {item.category && <Fact label="Categoria" value={item.category} />}
                  {item.domain && item.domain.length > 0 && <Fact label="Domínio" value={item.domain.join(', ')} />}
                  {item.origin && <Fact label="Origem" value={item.origin} />}
                  <Fact label="Aplicabilidade" value={item.applicable === false ? 'Não aplicável' : 'Aplicável'} />
                  {item.confidence && <Fact label="Confiança" value={confidenceLabels[item.confidence] ?? item.confidence} />}
                  {item.answer && <Fact label="Resposta" value={item.answer} />}
                  {item.interpretation && <Fact label="Interpretação" value={item.interpretation} />}
                  {item.risk && <Fact label="Risco" value={item.risk} />}
                </dl>

                {isEditing ? (
                  <form className="checklist-form" onSubmit={(event) => submit(event, item)} noValidate>
                    <Select label="Estado" value={draft.state} onChange={(event) => setDraft((d) => ({ ...d, state: event.target.value as ChecklistState }))}>
                      {CHECKLIST_STATES.map((state) => <option key={state} value={state}>{stateLabel(state)}</option>)}
                    </Select>
                    <Select label="Confiança" value={draft.confidence} onChange={(event) => setDraft((d) => ({ ...d, confidence: event.target.value as ChecklistConfidence }))}>
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
