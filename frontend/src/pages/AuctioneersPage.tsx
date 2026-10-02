import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Plus, Gavel, KeyRound, Eye, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import {
  listAuctioneers, createAuctioneer, addPortalAccess, revealPortalSecret,
  type Auctioneer, type PortalAccessCreate,
} from '../services/auctioneers'

const emptyForm = { name: '', document: '', company: '', registration: '', phone: '', email: '', website: '', address: '', observations: '' }
const emptyPortal: PortalAccessCreate = { portal: '', url: '', username: '', secret: '', access_type: '', two_factor_enabled: false }

export function AuctioneersPage() {
  const [auctioneers, setAuctioneers] = useState<Auctioneer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [fieldError, setFieldError] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const [portalFor, setPortalFor] = useState<number | null>(null)
  const [portal, setPortal] = useState<PortalAccessCreate>(emptyPortal)
  const [revealed, setRevealed] = useState<Record<number, string>>({})

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setAuctioneers(await listAuctioneers()) } catch (c) { setError(c instanceof Error ? c.message : 'Falha ao carregar.') } finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.name.trim() || form.name.trim().length < 2) { setFieldError('Informe o nome do leiloeiro.'); return }
    setSaving(true); setMessage('')
    try {
      await createAuctioneer({ ...form })
      setForm(emptyForm); setFormOpen(false); setMessage('Leiloeiro cadastrado.')
      await load()
    } catch (c) { setFieldError(c instanceof Error ? c.message : 'Não foi possível cadastrar.') } finally { setSaving(false) }
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

  const reveal = async (auctioneerId: number, portalId: number) => {
    try {
      const r = await revealPortalSecret(auctioneerId, portalId)
      setRevealed((cur) => ({ ...cur, [portalId]: r.secret ?? '(sem credencial)' }))
    } catch (c) { setMessage(c instanceof Error ? c.message : 'Falha ao recuperar credencial.') }
  }

  return (
    <Section title="Leiloeiros" description="Cadastro de leiloeiros, portais/acessos e documentos. Credenciais são protegidas." className="dossier-section"
      actions={<Button onClick={() => { setForm(emptyForm); setFieldError(''); setFormOpen(true) }}><Plus size={16} /> Novo leiloeiro</Button>}>
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
              <Button variant="ghost" type="button" onClick={() => setFormOpen(false)} disabled={saving}>Cancelar</Button>
              <Button type="submit" loading={saving}>Salvar leiloeiro</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? <LoadingState label="Carregando leiloeiros…" /> : error ? (
        <Card padding="lg"><Alert tone="danger" title="Não foi possível carregar">{error}</Alert><Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Tentar novamente</Button></Card>
      ) : auctioneers.length === 0 ? (
        <Card padding="none"><EmptyState title="Nenhum leiloeiro" description="Cadastre leiloeiros, seus portais e documentos." icon={<Gavel size={24} />} action={<Button onClick={() => setFormOpen(true)}><Plus size={16} /> Novo leiloeiro</Button>} /></Card>
      ) : (
        <div className="auctioneer-list">
          {auctioneers.map((a) => (
            <Card key={a.id} padding="lg" className="auctioneer-card">
              <div className="process-card-head">
                <div><p className="eyebrow">LEILOEIRO</p><h3>{a.name}</h3></div>
                <Badge tone={a.status === 'ATIVO' ? 'success' : 'neutral'} size="sm">{a.status}</Badge>
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
                    {revealed[p.id] !== undefined && <code className="portal-secret">{revealed[p.id]}</code>}
                  </div>
                ))}
                {portalFor === a.id ? (
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
