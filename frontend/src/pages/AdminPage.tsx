import { useCallback, useEffect, useState } from 'react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import {
  listMunicipalities, createMunicipality, listDebtTypes, createDebtType, listSources,
  listParameters, createParameter, updateParameter, parameterHistory,
  type Municipality, type DebtType, type DebtSource, type Parameter, type ParameterHistoryItem,
} from '../services/admin'

type Tab = 'overview' | 'municipios' | 'tipos' | 'fontes' | 'parametros'

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Visão geral' },
  { key: 'municipios', label: 'Municípios' },
  { key: 'fontes', label: 'Fontes de consulta' },
  { key: 'tipos', label: 'Tipos de débito' },
  { key: 'parametros', label: 'Parâmetros' },
]

export function AdminPage() {
  const [tab, setTab] = useState<Tab>('overview')
  // Token administrativo digitado pelo operador (proteção provisória até RBAC). Não persistido.
  const [adminToken, setAdminToken] = useState('')

  return (
    <div className="admin-module">
      <Alert tone="info">
        Área administrativa. As operações de <strong>escrita</strong> exigem o token de administração
        (proteção provisória até a frente de autenticação/RBAC). Nenhum segredo é armazenado aqui.
      </Alert>
      <Card padding="md">
        <Input
          label="Token de administração (X-Admin-Token)"
          type="password"
          placeholder="Necessário apenas para cadastrar/editar"
          value={adminToken}
          onChange={(e) => setAdminToken(e.target.value)}
        />
      </Card>
      <nav className="admin-tabs" aria-label="Administração">
        {TABS.map((t) => (
          <button key={t.key} type="button" className={`admin-tab ${tab === t.key ? 'admin-tab-active' : ''}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </nav>
      {tab === 'overview' && <OverviewTab />}
      {tab === 'municipios' && <MunicipiosTab token={adminToken} />}
      {tab === 'fontes' && <FontesTab />}
      {tab === 'tipos' && <TiposTab token={adminToken} />}
      {tab === 'parametros' && <ParametrosTab token={adminToken} />}
    </div>
  )
}

function useAsync<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const reload = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await loader()) } catch (e) { setError(e instanceof Error ? e.message : 'Falha ao carregar.') } finally { setLoading(false) }
  }, [loader])
  useEffect(() => { void reload() }, [reload])
  return { data, loading, error, reload }
}

function OverviewTab() {
  const mun = useAsync(useCallback(() => listMunicipalities(), []))
  const par = useAsync(useCallback(() => listParameters(), []))
  const typ = useAsync(useCallback(() => listDebtTypes(), []))
  return (
    <Section title="Visão geral" description="Resumo da cobertura e da parametrização.">
      <div className="admin-grid">
        <Card padding="md"><strong>{mun.data?.total ?? '—'}</strong><span>Municípios cadastrados</span></Card>
        <Card padding="md"><strong>{mun.data?.itens.filter((m) => m.coverage_active).length ?? '—'}</strong><span>Com cobertura ativa</span></Card>
        <Card padding="md"><strong>{typ.data?.total ?? '—'}</strong><span>Tipos de débito</span></Card>
        <Card padding="md"><strong>{par.data?.total ?? '—'}</strong><span>Parâmetros</span></Card>
      </div>
    </Section>
  )
}

function MunicipiosTab({ token }: { token: string }) {
  const { data, loading, error, reload } = useAsync(useCallback(() => listMunicipalities(), []))
  const [form, setForm] = useState({ name: '', state: '', ibge_code: '', coverage_active: true })
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(''); const [saving, setSaving] = useState(false)

  const submit = async () => {
    setErr(''); setMsg(''); setSaving(true)
    try {
      await createMunicipality({ ...form, coverage_active: form.coverage_active }, token)
      setMsg('Município cadastrado.'); setForm({ name: '', state: '', ibge_code: '', coverage_active: true }); await reload()
    } catch (e) { setErr(e instanceof Error ? e.message : 'Falha ao salvar.') } finally { setSaving(false) }
  }

  if (loading) return <LoadingState label="Carregando municípios..." />
  return (
    <Section title="Municípios e cobertura" description="Municípios atendidos. Cobertura independente por município.">
      {error && <Alert tone="danger">{error}</Alert>}
      {msg && <Alert tone="success">{msg}</Alert>}
      {err && <Alert tone="danger">{err}</Alert>}
      {(data?.itens.length ?? 0) === 0 ? <EmptyState title="Sem municípios" description="Cadastre o primeiro município." /> : (
        <table className="admin-table">
          <thead><tr><th>Município</th><th>UF</th><th>IBGE</th><th>Cobertura</th><th>Status</th></tr></thead>
          <tbody>
            {data?.itens.map((m: Municipality) => (
              <tr key={m.id}>
                <td>{m.name}</td><td>{m.state}</td><td>{m.ibge_code ?? '—'}</td>
                <td>{m.coverage_active ? <Badge tone="success">Ativa</Badge> : <Badge tone="neutral">Inativa</Badge>}</td>
                <td>{m.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Card padding="md" className="admin-form">
        <p className="admin-form-title">Novo município</p>
        <Input label="Nome" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <Input label="UF" maxLength={2} value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value.toUpperCase() })} />
        <Input label="Código IBGE" value={form.ibge_code} onChange={(e) => setForm({ ...form, ibge_code: e.target.value })} />
        <label className="admin-check"><input type="checkbox" checked={form.coverage_active} onChange={(e) => setForm({ ...form, coverage_active: e.target.checked })} /> Cobertura ativa</label>
        <Button onClick={submit} disabled={saving || !form.name || form.state.length !== 2}>Cadastrar</Button>
      </Card>
    </Section>
  )
}

function FontesTab() {
  const { data, loading, error } = useAsync(useCallback(() => listSources(), []))
  if (loading) return <LoadingState label="Carregando fontes..." />
  return (
    <Section title="Fontes de consulta" description="Cadastro de fontes por município/categoria. Nenhuma consulta é executada nesta etapa.">
      {error && <Alert tone="danger">{error}</Alert>}
      {(data?.itens.length ?? 0) === 0 ? <EmptyState title="Sem fontes" description="As fontes serão cadastradas na Etapa B (mapeamento por município)." /> : (
        <table className="admin-table">
          <thead><tr><th>Fonte</th><th>Município</th><th>Categoria</th><th>Tipo</th><th>Situação</th></tr></thead>
          <tbody>
            {data?.itens.map((s: DebtSource) => (
              <tr key={s.id}><td>{s.name}</td><td>#{s.municipality_id}</td><td>{s.debt_category ?? '—'}</td><td>{s.source_type}</td><td>{s.situation}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  )
}

function TiposTab({ token }: { token: string }) {
  const { data, loading, error, reload } = useAsync(useCallback(() => listDebtTypes(), []))
  const [form, setForm] = useState({ code: '', label: '', group: 'OUTRO' })
  const [err, setErr] = useState(''); const [saving, setSaving] = useState(false)
  const submit = async () => {
    setErr(''); setSaving(true)
    try { await createDebtType(form, token); setForm({ code: '', label: '', group: 'OUTRO' }); await reload() }
    catch (e) { setErr(e instanceof Error ? e.message : 'Falha ao salvar.') } finally { setSaving(false) }
  }
  if (loading) return <LoadingState label="Carregando tipos..." />
  return (
    <Section title="Tipos de débito" description="Catálogo administrável. Novas categorias sem alterar código.">
      {error && <Alert tone="danger">{error}</Alert>}
      {err && <Alert tone="danger">{err}</Alert>}
      <table className="admin-table">
        <thead><tr><th>Código</th><th>Rótulo</th><th>Grupo</th><th>Natureza</th><th>Financeiro</th></tr></thead>
        <tbody>
          {data?.itens.map((t: DebtType) => (
            <tr key={t.id}><td>{t.code}</td><td>{t.label}</td><td>{t.group}</td><td>{t.default_nature}</td><td>{t.impacts_finance ? 'Sim' : 'Não'}</td></tr>
          ))}
        </tbody>
      </table>
      <Card padding="md" className="admin-form">
        <p className="admin-form-title">Novo tipo</p>
        <Input label="Código" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
        <Input label="Rótulo" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
        <Input label="Grupo" value={form.group} onChange={(e) => setForm({ ...form, group: e.target.value.toUpperCase() })} />
        <Button onClick={submit} disabled={saving || !form.code || !form.label}>Cadastrar</Button>
      </Card>
    </Section>
  )
}

function ParametrosTab({ token }: { token: string }) {
  const { data, loading, error, reload } = useAsync(useCallback(() => listParameters(), []))
  const [editing, setEditing] = useState<Parameter | null>(null)
  const [editValue, setEditValue] = useState(''); const [justification, setJustification] = useState('')
  const [history, setHistory] = useState<ParameterHistoryItem[] | null>(null)
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(''); const [saving, setSaving] = useState(false)

  const openEdit = (p: Parameter) => { setEditing(p); setEditValue(p.value ?? ''); setJustification(''); setHistory(null); setErr(''); setMsg('') }
  const save = async () => {
    if (!editing) return
    setErr(''); setMsg(''); setSaving(true)
    try {
      await updateParameter(editing.id, { value: editValue, justification }, token)
      setMsg('Parâmetro atualizado (nova versão registrada).'); setEditing(null); await reload()
    } catch (e) { setErr(e instanceof Error ? e.message : 'Falha ao salvar.') } finally { setSaving(false) }
  }
  const openHistory = async (p: Parameter) => {
    try { const h = await parameterHistory(p.id); setHistory(h.historico); setEditing(p) } catch (e) { setErr(e instanceof Error ? e.message : 'Falha.') }
  }

  if (loading) return <LoadingState label="Carregando parâmetros..." />
  return (
    <Section title="Parâmetros" description="Catálogo central (transversal). Alterações geram nova versão + histórico; análises passadas são preservadas.">
      {error && <Alert tone="danger">{error}</Alert>}
      {msg && <Alert tone="success">{msg}</Alert>}
      {err && <Alert tone="danger">{err}</Alert>}
      {(data?.itens.length ?? 0) === 0 ? <EmptyState title="Sem parâmetros" description="Cadastre parâmetros de negócio aqui." /> : (
        <table className="admin-table">
          <thead><tr><th>Chave</th><th>Categoria</th><th>Escopo</th><th>Tipo</th><th>Valor</th><th>Versão</th><th></th></tr></thead>
          <tbody>
            {data?.itens.map((p: Parameter) => (
              <tr key={p.id}>
                <td>{p.key}</td><td>{p.category}</td><td>{p.scope}</td><td>{p.data_type}</td>
                <td>{p.value ?? p.default_value ?? '—'}{p.unit ? ` ${p.unit}` : ''}</td><td>v{p.version}</td>
                <td className="admin-row-actions">
                  <Button variant="ghost" onClick={() => openEdit(p)}>Editar</Button>
                  <Button variant="ghost" onClick={() => openHistory(p)}>Histórico</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {editing && (
        <Card padding="md" className="admin-form">
          <p className="admin-form-title">Editar {editing.key} (v{editing.version} → nova versão)</p>
          <Input label={`Valor (${editing.data_type})`} value={editValue} onChange={(e) => setEditValue(e.target.value)} />
          <Input label="Justificativa" value={justification} onChange={(e) => setJustification(e.target.value)} />
          <div className="admin-row-actions">
            <Button onClick={save} disabled={saving}>Salvar nova versão</Button>
            <Button variant="ghost" onClick={() => { setEditing(null); setHistory(null) }}>Cancelar</Button>
          </div>
          {history && (
            <div className="admin-history">
              <p className="admin-form-title">Histórico</p>
              <table className="admin-table">
                <thead><tr><th>v</th><th>Ação</th><th>De</th><th>Para</th><th>Ator</th><th>Justificativa</th></tr></thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.id}><td>v{h.version}</td><td>{h.action}</td><td>{h.previous_value ?? '—'}</td><td>{h.new_value ?? '—'}</td><td>{h.actor}</td><td>{h.justification ?? '—'}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </Section>
  )
}
