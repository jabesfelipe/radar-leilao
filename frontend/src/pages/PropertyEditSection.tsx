import { useEffect, useState, type FormEvent } from 'react'
import { Pencil, RefreshCw } from 'lucide-react'
import { Alert, Button, Card, Input, LoadingState, Section, Select, Textarea } from '../components/ui'
import {
  getPropertyDetail, updateProperty, updateAuction,
  type Property, type AuctionSummary,
} from '../services/properties'
import { SourcesSection } from './SourcesSection'

type PropertyEditSectionProps = {
  propertyId: number
  onSaved?: () => void
}

type PropForm = {
  title: string; address: string; city: string; state: string; property_type: string
  neighborhood: string; area_m2: string; private_area_m2: string; bedrooms: string
  parking_spots: string; description: string; origin: string; status: string
}

type AuctionForm = {
  auction_stage: string; appraisal_value: string; bid_value: string; acquisition_value: string
  commission_percent: string; commission_fixed: string; auctioneer: string
}

const numOrUndef = (v: string) => (v.trim() ? Number(v) : undefined)
const strOrUndef = (v: string) => (v.trim() ? v.trim() : undefined)

export function PropertyEditSection({ propertyId, onSaved }: PropertyEditSectionProps) {
  const [property, setProperty] = useState<Property | null>(null)
  const [auction, setAuction] = useState<AuctionSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [editProp, setEditProp] = useState(false)
  const [propForm, setPropForm] = useState<PropForm | null>(null)
  const [savingProp, setSavingProp] = useState(false)
  const [propMsg, setPropMsg] = useState('')
  const [propErr, setPropErr] = useState('')

  const [editAuction, setEditAuction] = useState(false)
  const [auctionForm, setAuctionForm] = useState<AuctionForm | null>(null)
  const [savingAuction, setSavingAuction] = useState(false)
  const [auctionMsg, setAuctionMsg] = useState('')
  const [auctionErr, setAuctionErr] = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try {
      const detail = await getPropertyDetail(propertyId)
      setProperty(detail.imovel)
      setAuction(detail.leilao)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o cadastro.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [propertyId])

  const beginEditProp = () => {
    if (!property) return
    setPropForm({
      title: property.title || '', address: property.address || '', city: property.city || '',
      state: property.state || '', property_type: property.property_type || '', neighborhood: property.neighborhood || '',
      area_m2: property.area_m2 == null ? '' : String(property.area_m2), private_area_m2: property.private_area_m2 == null ? '' : String(property.private_area_m2),
      bedrooms: property.bedrooms == null ? '' : String(property.bedrooms), parking_spots: property.parking_spots == null ? '' : String(property.parking_spots),
      description: property.description || '', origin: property.origin || '', status: property.status || '',
    })
    setPropErr(''); setPropMsg(''); setEditProp(true)
  }

  const submitProp = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!propForm) return
    setSavingProp(true); setPropErr(''); setPropMsg('')
    try {
      const updated = await updateProperty(propertyId, {
        title: propForm.title.trim(), address: propForm.address.trim(), city: propForm.city.trim(),
        state: propForm.state.trim(), property_type: propForm.property_type.trim(),
        neighborhood: strOrUndef(propForm.neighborhood), area_m2: numOrUndef(propForm.area_m2),
        private_area_m2: numOrUndef(propForm.private_area_m2), bedrooms: numOrUndef(propForm.bedrooms),
        parking_spots: numOrUndef(propForm.parking_spots), description: strOrUndef(propForm.description),
        origin: strOrUndef(propForm.origin), status: strOrUndef(propForm.status),
      })
      setProperty(updated)
      setEditProp(false)
      setPropMsg('Imóvel atualizado. O histórico registra a alteração (nenhuma análise foi criada).')
      onSaved?.()
    } catch (cause) {
      setPropErr(cause instanceof Error ? cause.message : 'Não foi possível atualizar o imóvel.')
    } finally {
      setSavingProp(false)
    }
  }

  const beginEditAuction = () => {
    if (!auction) return
    setAuctionForm({
      auction_stage: auction.auction_stage || '', appraisal_value: auction.appraisal_value == null ? '' : String(auction.appraisal_value),
      bid_value: auction.bid_value == null ? '' : String(auction.bid_value), acquisition_value: '',
      commission_percent: '', commission_fixed: '', auctioneer: auction.auctioneer || '',
    })
    setAuctionErr(''); setAuctionMsg(''); setEditAuction(true)
  }

  const submitAuction = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!auctionForm || !auction) return
    setSavingAuction(true); setAuctionErr(''); setAuctionMsg('')
    try {
      const { leilao } = await updateAuction(propertyId, auction.id, {
        auction_stage: strOrUndef(auctionForm.auction_stage),
        appraisal_value: numOrUndef(auctionForm.appraisal_value),
        bid_value: numOrUndef(auctionForm.bid_value),
        acquisition_value: numOrUndef(auctionForm.acquisition_value),
        commission_percent: numOrUndef(auctionForm.commission_percent),
        commission_fixed: numOrUndef(auctionForm.commission_fixed),
        auctioneer: strOrUndef(auctionForm.auctioneer),
      })
      setAuction(leilao)
      setEditAuction(false)
      setAuctionMsg('Leilão atualizado. O financeiro foi recalculado (nenhuma análise foi criada).')
      onSaved?.()
    } catch (cause) {
      setAuctionErr(cause instanceof Error ? cause.message : 'Não foi possível atualizar o leilão.')
    } finally {
      setSavingAuction(false)
    }
  }

  if (loading) return <Section title="Cadastro" description="Edição dos dados cadastrais do imóvel e do leilão." className="dossier-section"><LoadingState label="Carregando cadastro…" /></Section>
  if (error) {
    return (
      <Section title="Cadastro" description="Edição dos dados cadastrais do imóvel e do leilão." className="dossier-section">
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void load()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      </Section>
    )
  }

  return (
    <div className="financial-section">
      <Section title="Dados do imóvel" description="Edição cadastral. Não cria nova análise; gera histórico de alteração." className="dossier-section"
        actions={!editProp && <Button variant="secondary" onClick={beginEditProp}><Pencil size={16} /> Editar imóvel</Button>}>
        {propMsg && <Alert tone="success" title="Pronto" className="dossier-feedback">{propMsg}</Alert>}
        {property && !editProp && (
          <Card padding="lg" className="dossier-current">
            <dl className="dossier-facts">
              <Fact label="Identificação" value={property.title} />
              <Fact label="Cidade/UF" value={[property.city, property.state].filter(Boolean).join(' - ')} />
              <Fact label="Bairro" value={property.neighborhood} />
              <Fact label="Endereço" value={property.address} />
              <Fact label="Tipo" value={property.property_type} />
              <Fact label="Status" value={property.status} />
            </dl>
          </Card>
        )}
        {property && editProp && propForm && (
          <Card variant="elevated" padding="lg" className="dossier-form-card">
            <form className="dossier-form" onSubmit={submitProp} noValidate>
              <Input label="Identificação" value={propForm.title} onChange={(e) => setPropForm((f) => f && ({ ...f, title: e.target.value }))} required className="dossier-form-full" />
              <Input label="Endereço" value={propForm.address} onChange={(e) => setPropForm((f) => f && ({ ...f, address: e.target.value }))} />
              <Input label="Cidade" value={propForm.city} onChange={(e) => setPropForm((f) => f && ({ ...f, city: e.target.value }))} required />
              <Input label="UF" value={propForm.state} onChange={(e) => setPropForm((f) => f && ({ ...f, state: e.target.value }))} required />
              <Input label="Bairro" value={propForm.neighborhood} onChange={(e) => setPropForm((f) => f && ({ ...f, neighborhood: e.target.value }))} />
              <Input label="Tipo do imóvel" value={propForm.property_type} onChange={(e) => setPropForm((f) => f && ({ ...f, property_type: e.target.value }))} required />
              <Input label="Área total (m²)" type="number" step="0.01" value={propForm.area_m2} onChange={(e) => setPropForm((f) => f && ({ ...f, area_m2: e.target.value }))} />
              <Input label="Área privativa (m²)" type="number" step="0.01" value={propForm.private_area_m2} onChange={(e) => setPropForm((f) => f && ({ ...f, private_area_m2: e.target.value }))} />
              <Input label="Quartos" type="number" value={propForm.bedrooms} onChange={(e) => setPropForm((f) => f && ({ ...f, bedrooms: e.target.value }))} />
              <Input label="Vagas" type="number" value={propForm.parking_spots} onChange={(e) => setPropForm((f) => f && ({ ...f, parking_spots: e.target.value }))} />
              <Input label="Origem" value={propForm.origin} onChange={(e) => setPropForm((f) => f && ({ ...f, origin: e.target.value }))} />
              <Select label="Status" value={propForm.status} onChange={(e) => setPropForm((f) => f && ({ ...f, status: e.target.value }))}>
                <option value="EM_ANALISE">EM_ANALISE</option>
                <option value="ARREMATADO">ARREMATADO</option>
                <option value="DESCARTADO">DESCARTADO</option>
                <option value="MONITORANDO">MONITORANDO</option>
              </Select>
              <Textarea label="Descrição" value={propForm.description} onChange={(e) => setPropForm((f) => f && ({ ...f, description: e.target.value }))} className="dossier-form-full" />
              <div className="dossier-form-actions">
                {propErr && <Alert tone="danger">{propErr}</Alert>}
                <Button variant="ghost" type="button" onClick={() => setEditProp(false)} disabled={savingProp}>Cancelar</Button>
                <Button type="submit" loading={savingProp}>Salvar imóvel</Button>
              </div>
            </form>
          </Card>
        )}
      </Section>

      <Section title="Dados do leilão" description="Edição cadastral do leilão corrente. Recalcula o financeiro; não cria análise." className="dossier-section"
        actions={auction && !editAuction && <Button variant="secondary" onClick={beginEditAuction}><Pencil size={16} /> Editar leilão</Button>}>
        {auctionMsg && <Alert tone="success" title="Pronto" className="dossier-feedback">{auctionMsg}</Alert>}
        {!auction && <Card padding="lg"><p className="hub-muted">Nenhum leilão cadastrado para este imóvel.</p></Card>}
        {auction && !editAuction && (
          <Card padding="lg" className="dossier-current">
            <dl className="dossier-facts">
              <Fact label="Praça/Fase" value={auction.auction_stage} />
              <Fact label="Avaliação" value={auction.appraisal_value == null ? null : String(auction.appraisal_value)} />
              <Fact label="Lance" value={auction.bid_value == null ? null : String(auction.bid_value)} />
              <Fact label="Leiloeiro" value={auction.auctioneer} />
            </dl>
          </Card>
        )}
        {auction && editAuction && auctionForm && (
          <Card variant="elevated" padding="lg" className="dossier-form-card">
            <form className="dossier-form" onSubmit={submitAuction} noValidate>
              <Input label="Praça/Fase" value={auctionForm.auction_stage} onChange={(e) => setAuctionForm((f) => f && ({ ...f, auction_stage: e.target.value }))} />
              <Input label="Avaliação (R$)" type="number" step="0.01" value={auctionForm.appraisal_value} onChange={(e) => setAuctionForm((f) => f && ({ ...f, appraisal_value: e.target.value }))} />
              <Input label="Lance (R$)" type="number" step="0.01" value={auctionForm.bid_value} onChange={(e) => setAuctionForm((f) => f && ({ ...f, bid_value: e.target.value }))} />
              <Input label="Valor de arrematação (R$, opcional)" type="number" step="0.01" value={auctionForm.acquisition_value} onChange={(e) => setAuctionForm((f) => f && ({ ...f, acquisition_value: e.target.value }))} />
              <Input label="Comissão (%)" type="number" step="0.01" value={auctionForm.commission_percent} onChange={(e) => setAuctionForm((f) => f && ({ ...f, commission_percent: e.target.value }))} />
              <Input label="Comissão (R$ fixo)" type="number" step="0.01" value={auctionForm.commission_fixed} onChange={(e) => setAuctionForm((f) => f && ({ ...f, commission_fixed: e.target.value }))} />
              <Input label="Leiloeiro (texto)" value={auctionForm.auctioneer} onChange={(e) => setAuctionForm((f) => f && ({ ...f, auctioneer: e.target.value }))} />
              <div className="dossier-form-actions">
                {auctionErr && <Alert tone="danger">{auctionErr}</Alert>}
                <Button variant="ghost" type="button" onClick={() => setEditAuction(false)} disabled={savingAuction}>Cancelar</Button>
                <Button type="submit" loading={savingAuction}>Salvar leilão</Button>
              </div>
            </form>
          </Card>
        )}
      </Section>

      <SourcesSection propertyId={propertyId} />
    </div>
  )
}

function Fact({ label, value }: { label: string; value?: string | null }) {
  return <div><dt>{label}</dt><dd>{value || 'Não informado'}</dd></div>
}
