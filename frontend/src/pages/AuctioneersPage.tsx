import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Plus, Gavel, KeyRound, Eye, RefreshCw, Pencil, FileText, Trash2 } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import {
  listAuctioneers, createAuctioneer, updateAuctioneer, deleteAuctioneer, addPortalAccess, updatePortalAccess,
  deletePortalAccess, revealPortalSecret, addAuctioneerDocument, updateAuctioneerDocument, deleteAuctioneerDocument,
  type Auctioneer, type PortalAccess, type PortalAccessCreate, type AuctioneerCreate, type AuctioneerDocument,
} from '../services/auctioneers'

const emptyForm = { name: '', document: '', company: '', registration: '', phone: '', email: '', website: '', address: '', observations: '', status: 'ATIVO' }
const emptyPortal: PortalAccessCreate = { portal: '', url: '', username: '', secret: '', access_type: '', two_factor_enabled: false }
const emptyDoc = { doc_type: 'OUTROS', name: '', file_path: '', observations: '' }

type FormState = typeof emptyForm

export function AuctioneersPage() {
  const [auctioneers, setAuctioneers] = useState<Auctioneer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [fieldError, setFieldError] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  // Portal: criação (portalFor) ou edição (editingPortal).
  const [portalFor, setPortalFor] = useState<number | null>(null)
  const [portal, setPortal] = useState<PortalAccessCreate>(emptyPortal)
  const [editingPortal, setEditingPortal] = useState<{ auctioneerId: number; portalId: number } | null>(null)
  const [portalEdit, setPortalEdit] = useState<PortalAccessCreate>(emptyPortal)
  const [revealed, setRevealed] = useState<Record<number, string>>({})

  // Documentos (criação + edição de metadados).
  const [docFor, setDocFor] = useState<number | null>(null)
  const [doc, setDoc] = useState(emptyDoc)
  const [editingDocId, setEditingDocId] = useState<number | null>(null)
  const [docEdit, setDocEdit] = useState({ doc_type: '', name: '', observations: '' })

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setAuctioneers(await listAuctioneers()) } catch (c) { setError(c instanceof Error ? c.message : 'Falha ao carregar.') } finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  const openCreate = () => { setForm(emptyForm); setEditingId(null); setFieldError(''); setFormOpen(true) }
  const openEdit = (a: Auctioneer) => {
    setForm({
      name: a.name, document: a.document ?? '', company: a.company ?? '', registration: a.registration ?? '',
      phone: a.phone ?? '', email: a.email ?? '', website: a.website ?? '', address: a.address ?? '',
      observations: a.observations ?? '', status: a.status ?? 'ATIVO',
    })
    setEditingId(a.id); setFieldError(''); setFormOpen(true)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.name.trim() || form.name.trim().length < 2) { setFieldError('Informe o nome do leiloeiro.'); return }
    setSaving(true); setMessage('')
    try {
      const payload: AuctioneerCreate = { ...form }
      if (editingId) { await updateAuctioneer(editingId, payload); setMessage('Leiloeiro atualizado.') }
      else { await createAuctioneer(payload); setMessage('Leiloeiro cadastrado.') }
      setForm(emptyForm); setFormOpen(false); setEditingId(null)
      await load()
    } catch (c) { setFieldError(c instanceof Error ? c.message : 'Não foi possível salvar.') } finally { setSaving(false) }
  }

  const submitPortal = async (e: FormEvent, auctioneerId: number) => {
    e.preventDefault()
    if (!portal.portal.trim()) return
    setSaving(true)
    try {
      await addPortalAccess(auctioneerId, portal)
      setPortal(emptyPortal); setPortalFor(null); setMessage('Portal/acesso adicionado.')
      await load()
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao adicionar portal.') } finally { setSaving(false) }
  }

  const openPortalEdit = (auctioneerId: number, p: PortalAccess) => {
    setPortalEdit({
      portal: p.portal, url: p.url ?? '', username: p.username ?? '', secret: '',
      access_type: p.access_type ?? '', two_factor_enabled: p.two_factor_enabled, status: p.status,
    })
    setEditingPortal({ auctioneerId, portalId: p.id })
  }

  const submitPortalEdit = async (e: FormEvent) => {
    e.preventDefault()
    if (!editingPortal) return
    setSaving(true)
    try {
      // Só envia `secret` quando o operador digitou uma nova credencial (troca).
      const payload: PortalAccessCreate = { ...portalEdit }
      if (!payload.secret) delete payload.secret
      await updatePortalAccess(editingPortal.auctioneerId, editingPortal.portalId, payload)
      setEditingPortal(null); setMessage('Portal/acesso atualizado.')
      await load()
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao atualizar portal.') } finally { setSaving(false) }
  }

  const submitDoc = async (e: FormEvent, auctioneerId: number) => {
    e.preventDefault()
    if (!doc.name.trim()) return
    setSaving(true)
    try {
      await addAuctioneerDocument(auctioneerId, { ...doc })
      setDoc(emptyDoc); setDocFor(null); setMessage('Documento vinculado.')
      await load()
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao vincular documento.') } finally { setSaving(false) }
  }

  const reveal = async (auctioneerId: number, portalId: number) => {
    // TASK 75.1: credencial exige token de administração (header). Pede ao operador.
    const token = window.prompt('Token de administração (X-Portal-Admin-Token) para recuperar a credencial:')
    if (!token) return
    try {
      const r = await revealPortalSecret(auctioneerId, portalId, token)
      setRevealed((cur) => ({ ...cur, [portalId]: r.secret ?? '(sem credencial)' }))
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao recuperar credencial.') }
  }

  // TASK 75.2.1: exclusões (confirmação + atualização de lista + erro visível).
  const removeAuctioneer = async (a: Auctioneer) => {
    if (!window.confirm(`Excluir o leiloeiro "${a.name}"? Portais e documentos vinculados também serão removidos. A ação é registrada no histórico.`)) return
    setMessage('')
    try {
      await deleteAuctioneer(a.id)
      setMessage('Leiloeiro excluído.')
      await load()
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao excluir leiloeiro.') }
  }

  const removePortal = async (auctioneerId: number, p: PortalAccess) => {
    if (!window.confirm(`Excluir o portal "${p.portal}"? A ação é registrada no histórico (a credencial não é exposta).`)) return
    setMessage('')
    try {
      await deletePortalAccess(auctioneerId, p.id)
      setMessage('Portal/acesso excluído.')
      await load()
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao excluir portal.') }
  }

  const openDocEdit = (d: AuctioneerDocument) => {
    setEditingDocId(d.id)
    setDocEdit({ doc_type: d.doc_type ?? '', name: d.name ?? '', observations: d.observations ?? '' })
    setMessage('')
  }

  const submitDocEdit = async (e: FormEvent, auctioneerId: number, documentId: number) => {
    e.preventDefault()
    if (!docEdit.name.trim()) return
    setSaving(true)
    try {
      await updateAuctioneerDocument(auctioneerId, documentId, { doc_type: docEdit.doc_type, name: docEdit.name, observations: docEdit.observations })
      setEditingDocId(null); setMessage('Documento atualizado.')
      await load()
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao atualizar documento.') } finally { setSaving(false) }
  }

  const removeDoc = async (auctioneerId: number, d: AuctioneerDocument) => {
    if (!window.confirm(`Excluir o documento "${d.name}"? A ação é registrada no histórico.`)) return
    setMessage('')
    try {
      await deleteAuctioneerDocument(auctioneerId, d.id)
      setMessage('Documento excluído.')
      await load()
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao excluir documento.') }
  }

  return (
    <Section title="Leiloeiros" description="Cadastro de leiloeiros, portais/acessos e documentos. Credenciais são protegidas." className="dossier-section"
      actions={<Button onClick={openCreate}><Plus size={16} /> Novo leiloeiro</Button>}>
      {message && <Alert tone="success" title="Pronto" className="dossier-feedback">{message}</Alert>}

      {formOpen && (
        <Card variant="elevated" padding="lg" className="dossier-form-card">
          <form className="dossier-form" onSubmit={submit} noValidate>
            <Input label="Nome" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} error={fieldError} required className="dossier-form-full" />
            <Input label="CPF/CNPJ (opcional)" value={form.document} onChange={(e) => setForm((f) => ({ ...f, document: e.target.value }))} />
            <Input label="Empresa (opcional)" value={form.company} onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))} />
            <Input label="Registro profissional (opcional)" value={form.registration} onChange={(e) => setForm((f) => ({ ...f, registration: e.target.value }))} />
            <Input label="Telefone (opcional)" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
            <Input label="E-mail (opcional)" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
            <Input label="Site (opcional)" value={form.website} onChange={(e) => setForm((f) => ({ ...f, website: e.target.value }))} />
            <Input label="Endereço (opcional)" value={form.address} onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))} />
            <div className="dossier-form-actions">
              <Button variant="ghost" type="button" onClick={() => { setFormOpen(false); setEditingId(null) }} disabled={saving}>Cancelar</Button>
              <Button type="submit" loading={saving}>{editingId ? 'Salvar alterações' : 'Salvar leiloeiro'}</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? <LoadingState label="Carregando leiloeiros…" /> : error ? (
        <Card padding="lg"><Alert tone="danger" title="Não foi possível carregar">{error}</Alert><Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Tentar novamente</Button></Card>
      ) : auctioneers.length === 0 ? (
        <Card padding="none"><EmptyState title="Nenhum leiloeiro" description="Cadastre leiloeiros, seus portais e documentos." icon={<Gavel size={24} />} action={<Button onClick={openCreate}><Plus size={16} /> Novo leiloeiro</Button>} /></Card>
      ) : (
        <div className="auctioneer-list">
          {auctioneers.map((a) => (
            <Card key={a.id} padding="lg" className="auctioneer-card">
              <div className="process-card-head">
                <div><p className="eyebrow">LEILOEIRO</p><h3>{a.name}</h3></div>
                <div className="auctioneer-head-actions">
                  <Badge tone={a.status === 'ATIVO' ? 'success' : 'neutral'} size="sm">{a.status}</Badge>
                  <Button variant="ghost" size="sm" onClick={() => openEdit(a)}><Pencil size={14} /> Editar</Button>
                  <Button variant="ghost" size="sm" onClick={() => void removeAuctioneer(a)}><Trash2 size={14} /> Excluir</Button>
                </div>
              </div>
              <dl className="dossier-facts">
                <Fact label="Empresa" value={a.company} />
                <Fact label="Documento" value={a.document} />
                <Fact label="Registro" value={a.registration} />
                <Fact label="Telefone" value={a.phone} />
                <Fact label="E-mail" value={a.email} />
                <Fact label="Site" value={a.website} />
              </dl>

              <div className="auctioneer-portals">
                <p className="eyebrow">PORTAIS / ACESSOS</p>
                {(a.portais ?? []).length === 0 ? <p className="hub-muted">Nenhum portal cadastrado.</p> : (a.portais ?? []).map((p) => (
                  <div key={p.id} className="portal-row">
                    <KeyRound size={15} />
                    <div>
                      <strong>{p.portal}</strong>
                      <span>{p.username || 'sem usuário'} · {p.has_secret ? 'credencial salva' : 'sem credencial'}{p.two_factor_enabled ? ' · 2FA' : ''}</span>
                    </div>
                    {p.has_secret && (
                      <Button variant="ghost" size="sm" onClick={() => void reveal(a.id, p.id)}><Eye size={14} /> Ver credencial</Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => openPortalEdit(a.id, p)}><Pencil size={14} /> Editar</Button>
                    <Button variant="ghost" size="sm" onClick={() => void removePortal(a.id, p)}><Trash2 size={14} /> Excluir</Button>
                    {revealed[p.id] !== undefined && <code className="portal-secret">{revealed[p.id]}</code>}
                  </div>
                ))}

                {editingPortal?.auctioneerId === a.id ? (
                  <form className="portal-form" onSubmit={(e) => void submitPortalEdit(e)}>
                    <Input label="Portal" value={portalEdit.portal} onChange={(e) => setPortalEdit((p) => ({ ...p, portal: e.target.value }))} required />
                    <Input label="URL" value={portalEdit.url} onChange={(e) => setPortalEdit((p) => ({ ...p, url: e.target.value }))} />
                    <Input label="Usuário/E-mail" value={portalEdit.username} onChange={(e) => setPortalEdit((p) => ({ ...p, username: e.target.value }))} />
                    <Input label="Nova senha (deixe vazio p/ manter)" type="password" value={portalEdit.secret} onChange={(e) => setPortalEdit((p) => ({ ...p, secret: e.target.value }))} />
                    <div className="dossier-form-actions">
                      <Button variant="ghost" type="button" onClick={() => setEditingPortal(null)}>Cancelar</Button>
                      <Button type="submit" loading={saving}>Salvar portal</Button>
                    </div>
                  </form>
                ) : portalFor === a.id ? (
                  <form className="portal-form" onSubmit={(e) => void submitPortal(e, a.id)}>
                    <Input label="Portal" value={portal.portal} onChange={(e) => setPortal((p) => ({ ...p, portal: e.target.value }))} required />
                    <Input label="URL" value={portal.url} onChange={(e) => setPortal((p) => ({ ...p, url: e.target.value }))} />
                    <Input label="Usuário/E-mail" value={portal.username} onChange={(e) => setPortal((p) => ({ ...p, username: e.target.value }))} />
                    <Input label="Senha" type="password" value={portal.secret} onChange={(e) => setPortal((p) => ({ ...p, secret: e.target.value }))} />
                    <div className="dossier-form-actions">
                      <Button variant="ghost" type="button" onClick={() => setPortalFor(null)}>Cancelar</Button>
                      <Button type="submit" loading={saving}>Adicionar portal</Button>
                    </div>
                  </form>
                ) : (
                  <Button variant="secondary" size="sm" onClick={() => { setPortal(emptyPortal); setPortalFor(a.id) }}><Plus size={14} /> Adicionar portal</Button>
                )}
              </div>

              <div className="auctioneer-portals">
                <p className="eyebrow">DOCUMENTOS</p>
                {(a.documentos ?? []).length === 0 ? <p className="hub-muted">Nenhum documento vinculado.</p> : (a.documentos ?? []).map((d) => (
                  editingDocId === d.id ? (
                    <form key={d.id} className="portal-form" onSubmit={(e) => void submitDocEdit(e, a.id, d.id)}>
                      <Input label="Nome do documento" value={docEdit.name} onChange={(e) => setDocEdit((x) => ({ ...x, name: e.target.value }))} required />
                      <Input label="Tipo" value={docEdit.doc_type} onChange={(e) => setDocEdit((x) => ({ ...x, doc_type: e.target.value }))} />
                      <Input label="Observações (opcional)" value={docEdit.observations} onChange={(e) => setDocEdit((x) => ({ ...x, observations: e.target.value }))} />
                      <div className="dossier-form-actions">
                        <Button variant="ghost" type="button" onClick={() => setEditingDocId(null)}>Cancelar</Button>
                        <Button type="submit" loading={saving}>Salvar documento</Button>
                      </div>
                    </form>
                  ) : (
                    <div key={d.id} className="portal-row">
                      <FileText size={15} />
                      <div>
                        <strong>{d.name}</strong>
                        <span>{d.doc_type} · v{d.version}{d.observations ? ` · ${d.observations}` : ''}</span>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => openDocEdit(d)}><Pencil size={14} /> Editar</Button>
                      <Button variant="ghost" size="sm" onClick={() => void removeDoc(a.id, d)}><Trash2 size={14} /> Excluir</Button>
                    </div>
                  )
                ))}
                {docFor === a.id ? (
                  <form className="portal-form" onSubmit={(e) => void submitDoc(e, a.id)}>
                    <Input label="Nome do documento" value={doc.name} onChange={(e) => setDoc((d) => ({ ...d, name: e.target.value }))} required />
                    <Input label="Tipo" value={doc.doc_type} onChange={(e) => setDoc((d) => ({ ...d, doc_type: e.target.value }))} />
                    <Input label="Caminho/arquivo (opcional)" value={doc.file_path} onChange={(e) => setDoc((d) => ({ ...d, file_path: e.target.value }))} />
                    <Input label="Observações (opcional)" value={doc.observations} onChange={(e) => setDoc((d) => ({ ...d, observations: e.target.value }))} />
                    <div className="dossier-form-actions">
                      <Button variant="ghost" type="button" onClick={() => setDocFor(null)}>Cancelar</Button>
                      <Button type="submit" loading={saving}>Vincular documento</Button>
                    </div>
                  </form>
                ) : (
                  <Button variant="secondary" size="sm" onClick={() => { setDoc(emptyDoc); setDocFor(a.id) }}><Plus size={14} /> Vincular documento</Button>
                )}
              </div>
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
