import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { LinkIcon, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { Alert, Button, Card, EmptyState, Input, LoadingState, Section, Select } from '../components/ui'
import {
  listSources, updateSource, deleteSource,
  type PropertySource, type SourceType,
} from '../services/properties'

type SourcesSectionProps = {
  propertyId: number
}

const TYPES: SourceType[] = ['PAGINA_IMOVEL', 'EDITAL', 'MATRICULA', 'OUTRA']
type SourceForm = { source_type: SourceType; url: string; description: string; origin: string }
const emptyForm: SourceForm = { source_type: 'OUTRA', url: '', description: '', origin: '' }

export function SourcesSection({ propertyId }: SourcesSectionProps) {
  const [sources, setSources] = useState<PropertySource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saveError, setSaveError] = useState('')
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<SourceForm>(emptyForm)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setSources(await listSources(propertyId)) }
    catch (c) { setError(c instanceof Error ? c.message : 'Falha ao carregar as fontes.') }
    finally { setLoading(false) }
  }, [propertyId])

  useEffect(() => { void load() }, [load])

  const beginEdit = (s: PropertySource) => {
    setEditingId(s.id)
    setForm({ source_type: (s.source_type as SourceType) ?? 'OUTRA', url: s.url ?? '', description: s.description ?? '', origin: s.origin ?? '' })
    setSaveError(''); setMessage('')
  }

  const submitEdit = async (e: FormEvent, id: number) => {
    e.preventDefault()
    setSaving(true); setSaveError(''); setMessage('')
    try {
      const updated = await updateSource(propertyId, id, {
        source_type: form.source_type,
        url: form.url.trim() || undefined,
        description: form.description.trim() || undefined,
        origin: form.origin.trim() || undefined,
      })
      setSources((cur) => cur.map((s) => (s.id === id ? updated : s)))
      setEditingId(null)
      setMessage('Fonte atualizada. O histórico registra a alteração.')
    } catch (c) { setSaveError(c instanceof Error ? c.message : 'Falha ao atualizar a fonte.') }
    finally { setSaving(false) }
  }

  const remove = async (s: PropertySource) => {
    if (!window.confirm(`Excluir a fonte "${s.source_type}"? A ação é registrada no histórico.`)) return
    setSaveError(''); setMessage('')
    try {
      await deleteSource(propertyId, s.id)
      setSources((cur) => cur.filter((x) => x.id !== s.id))
      setMessage('Fonte excluída. O histórico registra a alteração.')
    } catch (c) { setSaveError(c instanceof Error ? c.message : 'Falha ao excluir a fonte.') }
  }

  return (
    <Section title="Fontes" description="Fontes oficiais do imóvel. Edição e exclusão geram histórico; não criam nova análise." className="dossier-section">
      {message && <Alert tone="success" title="Pronto" className="dossier-feedback">{message}</Alert>}
      {saveError && <Alert tone="danger">{saveError}</Alert>}

      {loading ? (
        <LoadingState label="Carregando fontes…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : sources.length === 0 ? (
        <Card padding="none"><EmptyState title="Nenhuma fonte cadastrada" description="As fontes são cadastradas no fluxo de cadastro do imóvel." icon={<LinkIcon size={24} />} /></Card>
      ) : (
        <div className="finance-list">
          {sources.map((s) => (
            <Card key={s.id} padding="md" className="finance-card">
              {editingId === s.id ? (
                <form className="dossier-form" onSubmit={(e) => void submitEdit(e, s.id)} noValidate>
                  <Select label="Tipo" value={form.source_type} onChange={(e) => setForm((f) => ({ ...f, source_type: e.target.value as SourceType }))}>
                    {TYPES.map((t) => <option key={t} value={t}>{t.split('_').join(' ')}</option>)}
                  </Select>
                  <Input label="URL (opcional)" value={form.url} onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))} className="dossier-form-full" />
                  <Input label="Descrição (opcional)" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
                  <Input label="Origem (opcional)" value={form.origin} onChange={(e) => setForm((f) => ({ ...f, origin: e.target.value }))} />
                  <div className="dossier-form-actions">
                    <Button variant="ghost" type="button" onClick={() => setEditingId(null)} disabled={saving}>Cancelar</Button>
                    <Button type="submit" loading={saving}>Salvar alterações</Button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="finance-card-head">
                    <strong>{s.source_type.split('_').join(' ')}</strong>
                    <div className="crud-actions">
                      <Button variant="ghost" size="sm" onClick={() => beginEdit(s)}><Pencil size={14} /> Editar</Button>
                      <Button variant="ghost" size="sm" onClick={() => void remove(s)}><Trash2 size={14} /> Excluir</Button>
                    </div>
                  </div>
                  <dl className="dossier-facts">
                    <Fact label="URL" value={s.url} />
                    <Fact label="Descrição" value={s.description} />
                    <Fact label="Origem" value={s.origin} />
                  </dl>
                </>
              )}
            </Card>
          ))}
        </div>
      )}
    </Section>
  )
}

function Fact({ label, value }: { label: string; value?: string | null }) {
  return <div><dt>{label}</dt><dd>{value || 'Não informado'}</dd></div>
}
