import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { BarChart3, ExternalLink, Plus, RefreshCw } from 'lucide-react'
import { Alert, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import { createComparable, formatMoney, getMarket, listComparables, type MarketComparable, type MarketResponse } from '../services/market'

type MarketSectionProps = {
  propertyId: number
}

type ComparableForm = {
  kind: string
  price: string
  rent: string
  area_m2: string
  source: string
  url: string
}

const initialForm: ComparableForm = { kind: '', price: '', rent: '', area_m2: '', source: '', url: '' }

function formatArea(value?: number | string) {
  if (value === undefined || value === null || value === '') return 'Não informado'
  const numeric = Number(value)
  return Number.isNaN(numeric) ? String(value) : `${numeric} m²`
}

export function MarketSection({ propertyId }: MarketSectionProps) {
  const [comparables, setComparables] = useState<MarketComparable[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<ComparableForm>(initialForm)
  const [fieldError, setFieldError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [market, setMarket] = useState<MarketResponse['mercado'] | null>(null)

  const loadComparables = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [comps, marketData] = await Promise.all([listComparables(propertyId), getMarket(propertyId)])
      setComparables(comps)
      setMarket(marketData.mercado)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os comparáveis.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadComparables() }, [loadComparables])

  const openForm = () => {
    setForm(initialForm)
    setFieldError('')
    setSaveError('')
    setSuccessMessage('')
    setFormOpen(true)
  }

  const updateField = (field: keyof ComparableForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    if (field === 'kind') setFieldError('')
    setSaveError('')
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!form.kind.trim()) {
      setFieldError('Informe o tipo do comparável.')
      return
    }
    setSaving(true)
    setSaveError('')
    setSuccessMessage('')
    try {
      const created = await createComparable(propertyId, {
        kind: form.kind.trim(),
        price: form.price.trim() ? Number(form.price) : undefined,
        rent: form.rent.trim() ? Number(form.rent) : undefined,
        area_m2: form.area_m2.trim() ? Number(form.area_m2) : undefined,
        source: form.source.trim() || undefined,
        url: form.url.trim() || undefined,
      })
      setComparables((current) => [...current, created])
      setFormOpen(false)
      setForm(initialForm)
      setSuccessMessage('Comparável cadastrado com sucesso.')
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível cadastrar o comparável.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Mercado" description="Comparáveis de mercado cadastrados para o imóvel." className="dossier-section" actions={<Button onClick={openForm}><Plus size={16} /> Novo comparável</Button>}>
      {successMessage && <Alert tone="success" title="Cadastro concluído" className="dossier-feedback">{successMessage}</Alert>}

      {market && (
        <Card padding="lg" className="market-quality">
          <dl className="dossier-facts">
            <Fact label="Comparáveis de venda" value={String(market.venda?.quantidade ?? 0)} />
            <Fact label="Preço médio" value={formatMoney(market.venda?.preco_medio ?? null)} />
            <Fact label="Preço mediano" value={formatMoney(market.venda?.preco_mediano ?? null)} />
            <Fact label="Preço/m² mediano" value={formatMoney(market.venda?.preco_m2_mediano ?? null)} />
            <Fact label="Comparáveis de aluguel" value={String(market.aluguel?.quantidade ?? 0)} />
            <Fact label="Aluguel mediano" value={formatMoney(market.aluguel?.aluguel_mediano ?? null)} />
          </dl>
          {market.venda?.qualidade && !market.venda.qualidade.amostra_suficiente && (
            <Alert tone="warning" title="Amostra insuficiente">A amostra é apenas indicativa, não conclusiva. Média/mediana não constituem avaliação definitiva de mercado.</Alert>
          )}
          {market.venda?.qualidade?.dispersao_elevada && (
            <Alert tone="warning" title="Dispersão elevada">Os comparáveis têm alta variação de preço (possível heterogeneidade ou valores discrepantes).</Alert>
          )}
          {market.observacao && <p className="market-obs">{market.observacao}</p>}
        </Card>
      )}

      {formOpen && (
        <Card variant="elevated" padding="lg" className="dossier-form-card">
          <form className="dossier-form" onSubmit={handleSubmit} noValidate>
            <Input label="Tipo" placeholder="Ex.: VENDA" value={form.kind} onChange={(event) => updateField('kind', event.target.value)} error={fieldError} required />
            <Input label="Preço (opcional)" type="number" step="0.01" value={form.price} onChange={(event) => updateField('price', event.target.value)} />
            <Input label="Aluguel (opcional)" type="number" step="0.01" value={form.rent} onChange={(event) => updateField('rent', event.target.value)} />
            <Input label="Área m² (opcional)" type="number" step="0.01" value={form.area_m2} onChange={(event) => updateField('area_m2', event.target.value)} />
            <Input label="Fonte (opcional)" value={form.source} onChange={(event) => updateField('source', event.target.value)} />
            <Input label="URL (opcional)" value={form.url} onChange={(event) => updateField('url', event.target.value)} className="dossier-form-full" />
            <div className="dossier-form-actions">
              {saveError && <Alert tone="danger">{saveError}</Alert>}
              <Button variant="ghost" type="button" onClick={() => setFormOpen(false)} disabled={saving}>Cancelar</Button>
              <Button type="submit" loading={saving}>Salvar comparável</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingState label="Carregando comparáveis…" />
      ) : error ? (
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadComparables()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : comparables.length === 0 ? (
        <Card padding="none"><EmptyState title="Nenhum comparável cadastrado" description="Cadastre referências de mercado para compor o dossiê." icon={<BarChart3 size={24} />} action={<Button onClick={openForm}><Plus size={16} /> Novo comparável</Button>} /></Card>
      ) : (
        <div className="finance-list">
          {comparables.map((comparable) => (
            <Card key={comparable.id} padding="md" className="finance-card">
              <div className="finance-card-head">
                <strong>{comparable.kind}</strong>
                {comparable.url && <a className="market-link" href={comparable.url} target="_blank" rel="noreferrer">Fonte <ExternalLink size={13} /></a>}
              </div>
              <dl className="dossier-facts">
                <Fact label="Preço" value={formatMoney(comparable.price)} />
                <Fact label="Aluguel" value={comparable.rent == null || comparable.rent === '' ? 'Não informado' : formatMoney(comparable.rent)} />
                <Fact label="Área" value={formatArea(comparable.area_m2)} />
                <Fact label="Fonte" value={comparable.source} />
              </dl>
            </Card>
          ))}
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
