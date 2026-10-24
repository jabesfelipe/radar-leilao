import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { BookOpen, ExternalLink, Scale, Search } from 'lucide-react'
import { Alert, Badge, Button, Card, LoadingState, Section, Select } from '../components/ui'
import {
  getLibrary, getPropertyLegalCentral, searchLibrary,
  type LegalProvision, type LegalRule, type LibraryOverview,
  type LibrarySearch, type PropertyLegalCentral,
} from '../services/legal'

type Props = { propertyId: number }

const CONTEXTS = ['', 'LEILAO', 'ARREMATACAO', 'MATRICULA', 'CONSOLIDACAO', 'DESOCUPACAO', 'POSSE', 'TRIBUTARIO', 'LOCACAO']

const ruleTone: Record<string, 'neutral' | 'warning' | 'danger' | 'info' | 'success'> = {
  REQUISITO: 'info',
  RISCO: 'danger',
  ORIENTACAO: 'neutral',
  PRAZO: 'warning',
  RESPONSABILIDADE: 'warning',
}

const verificationLabel: Record<string, string> = {
  VERIFICADO: 'Verificado na fonte oficial',
  PENDENTE: 'Pendente de curadoria',
  DESATUALIZADO: 'Possivelmente desatualizado',
}

// Renderiza um dispositivo distinguindo SEMPRE texto oficial de orientação prática.
function ProvisionBlock({ provision }: { provision: LegalProvision }) {
  return (
    <div className="legal-provision">
      <div className="dossier-current-head">
        <div>
          <p className="eyebrow">{provision.fonte ? `${provision.fonte.rotulo} · ` : ''}{provision.referencia}</p>
          {provision.titulo && <strong>{provision.titulo}</strong>}
        </div>
        <Badge tone={provision.verificacao === 'VERIFICADO' ? 'success' : 'warning'} size="sm">
          {verificationLabel[provision.verificacao] ?? provision.verificacao}
        </Badge>
      </div>
      {provision.texto_oficial && (
        <blockquote className="legal-official">
          <span className="eyebrow">TEXTO OFICIAL</span>
          <p>{provision.texto_oficial}</p>
        </blockquote>
      )}
      {provision.orientacao_pratica && (
        <div className="legal-practical">
          <span className="eyebrow">ORIENTAÇÃO PRÁTICA (MÉTODO RADAR)</span>
          <p>{provision.orientacao_pratica}</p>
        </div>
      )}
      <div className="legal-meta">
        {(provision.contextos || []).map((c) => <Badge key={c} tone="neutral" size="sm">{c}</Badge>)}
        {provision.fonte?.url_oficial && (
          <a className="link-button" href={provision.fonte.url_oficial} target="_blank" rel="noreferrer">
            <ExternalLink size={14} /> Fonte oficial
          </a>
        )}
        {typeof provision.similaridade === 'number' && (
          <span className="wizard-muted">similaridade {Math.round(provision.similaridade * 100)}%</span>
        )}
      </div>
    </div>
  )
}

function RuleBlock({ rule }: { rule: LegalRule }) {
  return (
    <Card padding="lg" className="finance-card legal-rule-card">
      <div className="dossier-current-head">
        <div><p className="eyebrow">{rule.titulo}</p></div>
        <Badge tone={ruleTone[rule.tipo] ?? 'neutral'} size="sm">{rule.tipo}</Badge>
      </div>
      <p>{rule.enunciado}</p>
      {rule.severidade && <div className="wizard-muted">Severidade: <strong>{rule.severidade}</strong></div>}
      {rule.base_legal && <ProvisionBlock provision={rule.base_legal} />}
      {Array.isArray(rule.itens_checklist) && rule.itens_checklist.length > 0 && (
        <div className="legal-meta">
          <span className="wizard-muted">Checklist:</span>
          {rule.itens_checklist.map((l) => (
            <Badge key={l.canonical_key} tone="info" size="sm">{l.canonical_key}</Badge>
          ))}
        </div>
      )}
    </Card>
  )
}

export function CentralJuridicaSection({ propertyId }: Props) {
  const [central, setCentral] = useState<PropertyLegalCentral | null>(null)
  const [library, setLibrary] = useState<LibraryOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [query, setQuery] = useState('')
  const [context, setContext] = useState('')
  const [search, setSearch] = useState<LibrarySearch | null>(null)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [c, lib] = await Promise.all([getPropertyLegalCentral(propertyId), getLibrary()])
      setCentral(c); setLibrary(lib)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar a Central Jurídica.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void load() }, [load])

  const runSearch = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!query.trim() && !context) { setSearch(null); return }
    setSearching(true); setSearchError('')
    try { setSearch(await searchLibrary(query.trim(), context || undefined)) }
    catch (cause) { setSearchError(cause instanceof Error ? cause.message : 'Falha na busca.') }
    finally { setSearching(false) }
  }

  const cobertura = library?.cobertura_checklist ?? {}
  const coberturaResumo = useMemo(() => {
    if (!library) return ''
    return `${library.itens_checklist_cobertos} de ${library.itens_checklist_total} itens do checklist com base legal associada`
  }, [library])

  if (loading) return <Section title="Central Jurídica" className="dossier-section"><LoadingState label="Carregando base jurídica…" /></Section>
  if (error) {
    return (
      <Section title="Central Jurídica" className="dossier-section">
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void load()}>Tentar novamente</Button>
        </Card>
      </Section>
    )
  }

  const sintese = central?.sintese_juridica

  return (
    <Section
      title="Central Jurídica"
      description="Base de conhecimento jurídico aplicada à decisão: a norma aparece em contexto (checklist, desocupação, tributário), com texto oficial separado da orientação prática. Nunca substitui a leitura do edital/matrícula."
      className="dossier-section"
    >
      {/* 1) Situação jurídica do imóvel, reaproveitando a síntese determinística. */}
      {sintese && (
        <Card padding="lg" className="finance-card">
          <p className="eyebrow"><Scale size={14} /> SITUAÇÃO JURÍDICA DO IMÓVEL</p>
          <div className="wizard-muted">
            Processos: {sintese.processos_encontrados} (relevantes: {sintese.processos_relevantes}) · Correlação: <strong>{sintese.correlacao}</strong> ·
            Situação: <strong>{sintese.situacao_imovel === 'CONFIRMADA' ? 'Confirmada' : 'Não confirmada'}</strong> ·
            Impacto financeiro: {sintese.impacto_financeiro === 'NAO_QUANTIFICADO' ? 'não quantificado' : sintese.impacto_financeiro}
          </div>
          {sintese.pendencias.length > 0 && (
            <div className="finance-pendencias">
              <strong>Pendências jurídicas</strong>
              <ul>{sintese.pendencias.map((p, i) => <li key={i}>{p}</li>)}</ul>
            </div>
          )}
          {sintese.diligencia_recomendada && <Alert tone="info" title="Diligência recomendada">{sintese.diligencia_recomendada}</Alert>}
        </Card>
      )}

      {/* 2) Itens do checklist com base legal associada (conhecimento em contexto). */}
      {central && central.itens_com_base_legal.length > 0 && (
        <div className="finance-list">
          <p className="eyebrow">BASE LEGAL POR ITEM DO CHECKLIST</p>
          {central.itens_com_base_legal.map((item) => (
            <Card key={item.canonical_key} padding="lg" className="finance-card">
              <div className="dossier-current-head">
                <div><p className="eyebrow">{item.canonical_key}</p><strong>{item.pergunta}</strong></div>
                <Badge tone="neutral" size="sm">{item.estado}</Badge>
              </div>
              {item.referencias.map((rule) => <RuleBlock key={rule.id} rule={rule} />)}
            </Card>
          ))}
        </div>
      )}

      {/* 3) Biblioteca jurídica: busca + fontes/dispositivos curados. */}
      <Card padding="lg" className="finance-card">
        <p className="eyebrow"><BookOpen size={14} /> BIBLIOTECA JURÍDICA</p>
        {library && <div className="wizard-muted">{coberturaResumo} · {library.total_fontes} fontes · {library.total_dispositivos} dispositivos · {library.total_regras} regras</div>}
        <form className="dossier-form" onSubmit={runSearch} noValidate style={{ marginTop: 12 }}>
          <label className="field" style={{ flex: 1 }}>
            <span>Buscar na base legal</span>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="ex.: taxa de ocupação, evicção, dois leilões" />
          </label>
          <Select label="Contexto" value={context} onChange={(e) => setContext(e.target.value)}>
            {CONTEXTS.map((c) => <option key={c || 'todos'} value={c}>{c || 'Todos os contextos'}</option>)}
          </Select>
          <div className="dossier-form-actions">
            <Button type="submit" loading={searching}><Search size={14} /> Buscar</Button>
          </div>
        </form>
        {searchError && <Alert tone="danger" title="Falha na busca">{searchError}</Alert>}
        {search && (
          <div className="legal-search-results">
            <div className="wizard-muted">{search.total} resultado(s) · modo {search.modo_busca === 'VETORIAL' ? 'semântico' : 'textual'}</div>
            {search.resultados.map((p) => <ProvisionBlock key={p.id} provision={p} />)}
            {search.total === 0 && <p className="wizard-muted">Nenhum dispositivo encontrado para a busca.</p>}
          </div>
        )}
      </Card>

      {/* Fontes curadas (sempre visíveis, mesmo sem busca). */}
      {library && (
        <div className="finance-list">
          {library.fontes.map((fonte) => (
            <Card key={fonte.id} padding="lg" className="finance-card">
              <div className="dossier-current-head">
                <div>
                  <p className="eyebrow">{fonte.tipo} · {fonte.ano ?? '—'}</p>
                  <strong>{fonte.rotulo}</strong>
                </div>
                <Badge tone={fonte.vigente ? 'success' : 'warning'} size="sm">{fonte.vigente ? 'Vigente' : 'Revogada/alterada'}</Badge>
              </div>
              {fonte.resumo && <p className="wizard-muted">{fonte.resumo}</p>}
              {fonte.dispositivos.map((p) => <ProvisionBlock key={p.id} provision={p} />)}
            </Card>
          ))}
        </div>
      )}

      {Object.keys(cobertura).length === 0 && (
        <Alert tone="info" title="Base em curadoria">A base legal curada ainda não possui vínculos com o checklist deste ambiente.</Alert>
      )}
    </Section>
  )
}
