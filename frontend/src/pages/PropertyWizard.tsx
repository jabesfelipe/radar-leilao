import { useMemo, useState } from 'react'
import { Check, Plus, Trash2, Upload } from 'lucide-react'
import { Alert, Button, Card, Input, Section, Select, Textarea } from '../components/ui'
import {
  createPropertyFull,
  type PropertyFullCreate,
  type SourceType,
} from '../services/properties'
import { uploadDocument } from '../services/documents'

type PropertyWizardProps = {
  onCancel: () => void
  onCreated: (id: number) => void
}

type WizardForm = {
  // Dados básicos
  title: string
  address: string
  city: string
  state: string
  property_type: string
  neighborhood: string
  area_m2: string
  private_area_m2: string
  bedrooms: string
  parking_spots: string
  description: string
  // Identificação na origem
  origin: string
  origin_property_code: string
  inscription: string
  modality: string
  system: string
  // Dados do leilão
  appraisal_value: string
  first_auction_date: string
  first_auction_value: string
  second_auction_date: string
  second_auction_value: string
  auctioneer: string
  // Edital
  notice_identifier: string
  notice_item: string
  // Matrícula
  registration_number: string
  registry_office: string
  registration_comarca: string
}

type SourceRow = { source_type: SourceType; url: string; description: string }

type DocRow = { file: File; document_type: string }

const initialForm: WizardForm = {
  title: '',
  address: '',
  city: '',
  state: '',
  property_type: 'Apartamento',
  neighborhood: '',
  area_m2: '',
  private_area_m2: '',
  bedrooms: '',
  parking_spots: '',
  description: '',
  origin: '',
  origin_property_code: '',
  inscription: '',
  modality: '',
  system: '',
  appraisal_value: '',
  first_auction_date: '',
  first_auction_value: '',
  second_auction_date: '',
  second_auction_value: '',
  auctioneer: '',
  notice_identifier: '',
  notice_item: '',
  registration_number: '',
  registry_office: '',
  registration_comarca: '',
}

const steps = ['Dados básicos', 'Dados do leilão', 'Fontes', 'Documentos', 'Revisão']

const propertyTypes = ['Apartamento', 'Casa', 'Terreno', 'Comercial', 'Vaga de garagem', 'Outro']
const sourceTypeLabels: Record<SourceType, string> = {
  PAGINA_IMOVEL: 'Página do imóvel',
  EDITAL: 'Edital',
  MATRICULA: 'Matrícula',
  OUTRA: 'Outra',
}

function money(value?: string) {
  if (!value || !value.trim()) return 'Não informado'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return value
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(numeric)
}

function toNumber(value: string): number | undefined {
  if (!value.trim()) return undefined
  const numeric = Number(value)
  return Number.isNaN(numeric) ? undefined : numeric
}

function isValidUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

export function PropertyWizard({ onCancel, onCreated }: PropertyWizardProps) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState<WizardForm>(initialForm)
  const [sources, setSources] = useState<SourceRow[]>([])
  const [docs, setDocs] = useState<DocRow[]>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  // Resultado do envio dos documentos após o cadastro (não esconde falhas).
  const [uploadResult, setUploadResult] = useState<{ propertyId: number; sent: number; failed: string[] } | null>(null)

  const update = (field: keyof WizardForm, value: string) => {
    setForm((current) => ({ ...current, [field]: field === 'state' ? value.toUpperCase() : value }))
    setErrors((current) => ({ ...current, [field]: '' }))
    setSaveError('')
  }

  const validateBasics = () => {
    const next: Record<string, string> = {}
    if (form.title.trim().length < 2) next.title = 'Informe uma identificação com pelo menos 2 caracteres.'
    if (!form.city.trim()) next.city = 'Informe a cidade.'
    if (form.state.trim().length !== 2) next.state = 'Informe a UF com 2 caracteres.'
    if (!form.property_type.trim()) next.property_type = 'Selecione o tipo do imóvel.'
    for (const field of ['area_m2', 'private_area_m2', 'bedrooms', 'parking_spots'] as const) {
      if (form[field].trim() && Number.isNaN(Number(form[field]))) next[field] = 'Informe um número válido.'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const validateAuction = () => {
    const next: Record<string, string> = {}
    for (const field of ['appraisal_value', 'first_auction_value', 'second_auction_value'] as const) {
      if (form[field].trim() && Number.isNaN(Number(form[field]))) next[field] = 'Informe um valor válido.'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const validateSources = () => {
    const next: Record<string, string> = {}
    sources.forEach((source, index) => {
      if (source.url.trim() && !isValidUrl(source.url.trim())) next[`source-${index}`] = 'URL inválida (use http:// ou https://).'
    })
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const goNext = () => {
    if (step === 0 && !validateBasics()) return
    if (step === 1 && !validateAuction()) return
    if (step === 2 && !validateSources()) return
    setStep((current) => Math.min(current + 1, steps.length - 1))
  }

  const goBack = () => setStep((current) => Math.max(current - 1, 0))

  const addSource = () => setSources((current) => [...current, { source_type: 'PAGINA_IMOVEL', url: '', description: '' }])
  const updateSource = (index: number, patch: Partial<SourceRow>) => {
    setSources((current) => current.map((item, i) => (i === index ? { ...item, ...patch } : item)))
    setErrors((current) => ({ ...current, [`source-${index}`]: '' }))
  }
  const removeSource = (index: number) => setSources((current) => current.filter((_, i) => i !== index))

  const onDocFiles = (fileList: FileList | null) => {
    if (!fileList) return
    const added: DocRow[] = Array.from(fileList).map((file) => ({ file, document_type: 'OUTRO' }))
    setDocs((current) => [...current, ...added])
  }
  const updateDoc = (index: number, document_type: string) =>
    setDocs((current) => current.map((item, i) => (i === index ? { ...item, document_type } : item)))
  const removeDoc = (index: number) => setDocs((current) => current.filter((_, i) => i !== index))

  const payload = useMemo<PropertyFullCreate>(() => {
    const leilaoEntries = {
      appraisal_value: toNumber(form.appraisal_value),
      first_auction_date: form.first_auction_date || undefined,
      first_auction_value: toNumber(form.first_auction_value),
      second_auction_date: form.second_auction_date || undefined,
      second_auction_value: toNumber(form.second_auction_value),
      auctioneer: form.auctioneer.trim() || undefined,
    }
    const hasLeilao = Object.values(leilaoEntries).some((value) => value !== undefined)
    const hasEdital = form.notice_identifier.trim() || form.notice_item.trim()
    const hasMatricula = form.registration_number.trim() || form.registry_office.trim() || form.registration_comarca.trim()
    return {
      imovel: {
        title: form.title.trim(),
        address: form.address.trim() || undefined,
        city: form.city.trim(),
        state: form.state.trim().toUpperCase(),
        property_type: form.property_type,
        neighborhood: form.neighborhood.trim() || undefined,
        area_m2: toNumber(form.area_m2),
        private_area_m2: toNumber(form.private_area_m2),
        bedrooms: toNumber(form.bedrooms),
        parking_spots: toNumber(form.parking_spots),
        description: form.description.trim() || undefined,
        origin: form.origin.trim() || undefined,
        origin_property_code: form.origin_property_code.trim() || undefined,
        inscription: form.inscription.trim() || undefined,
        modality: form.modality.trim() || undefined,
        system: form.system.trim() || undefined,
      },
      leilao: hasLeilao ? leilaoEntries : undefined,
      edital: hasEdital
        ? { identifier: form.notice_identifier.trim() || undefined, item: form.notice_item.trim() || undefined }
        : undefined,
      matricula: hasMatricula
        ? {
            registration_number: form.registration_number.trim() || undefined,
            registry_office: form.registry_office.trim() || undefined,
            comarca: form.registration_comarca.trim() || undefined,
          }
        : undefined,
      fontes: sources
        .filter((source) => source.url.trim() || source.description.trim())
        .map((source) => ({
          source_type: source.source_type,
          url: source.url.trim() || undefined,
          description: source.description.trim() || undefined,
        })),
    }
  }, [form, sources])

  const handleSubmit = async () => {
    setSaving(true)
    setSaveError('')
    try {
      const created = await createPropertyFull(payload)
      // Documentos são enviados após o cadastro (etapa separada, não transacional):
      // uma falha de upload NÃO desfaz o imóvel. Contabilizamos enviados/falhados
      // para informar o usuário — a falha nunca é escondida.
      const failed: string[] = []
      let sent = 0
      for (const doc of docs) {
        try {
          await uploadDocument(created.id, { file: doc.file, document_type: doc.document_type, source: 'Cadastro do imóvel' })
          sent += 1
        } catch {
          failed.push(doc.file.name)
        }
      }
      if (failed.length > 0) {
        // Mantém o usuário na tela para ver o aviso antes de ir ao dossiê.
        setUploadResult({ propertyId: created.id, sent, failed })
        setSaving(false)
        return
      }
      onCreated(created.id)
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : 'Não foi possível salvar o imóvel.')
      setSaving(false)
    }
  }

  if (uploadResult) {
    return (
      <Card variant="elevated" padding="lg" className="property-form-card wizard-card">
        <Section title="Imóvel cadastrado" description="O imóvel foi criado. Alguns documentos não foram enviados.">
          <Alert tone="warning" title="Atenção com os documentos">
            <p>
              Imóvel cadastrado com sucesso.{uploadResult.sent > 0 ? ` ${uploadResult.sent} documento(s) enviado(s).` : ''}
            </p>
            <p>
              {uploadResult.failed.length} documento(s) não foram enviados:
            </p>
            <ul className="wizard-failed-list">
              {uploadResult.failed.map((name) => <li key={name}>{name}</li>)}
            </ul>
            <p>Você pode reenviá-los pelo Dossiê do imóvel.</p>
          </Alert>
          <div className="dossier-form-actions wizard-actions">
            <Button onClick={() => onCreated(uploadResult.propertyId)}>Ir para o dossiê</Button>
          </div>
        </Section>
      </Card>
    )
  }

  return (
    <Card variant="elevated" padding="lg" className="property-form-card wizard-card">
      <Section
        title="Novo imóvel"
        description="Cadastro guiado do imóvel de leilão. Só nome, cidade, UF e tipo são obrigatórios."
        actions={<Button variant="ghost" onClick={onCancel} disabled={saving}>Cancelar</Button>}
      >
        <nav className="wizard-steps" aria-label="Etapas do cadastro">
          {steps.map((label, index) => (
            <button
              key={label}
              type="button"
              className={`wizard-step ${index === step ? 'wizard-step-active' : ''} ${index < step ? 'wizard-step-done' : ''}`}
              onClick={() => index < step && setStep(index)}
              aria-current={index === step ? 'step' : undefined}
            >
              <span className="wizard-step-index">{index < step ? <Check size={14} /> : index + 1}</span>
              {label}
            </button>
          ))}
        </nav>

        {step === 0 && (
          <div className="dossier-form wizard-form">
            <Input label="Nome / identificação" value={form.title} onChange={(e) => update('title', e.target.value)} error={errors.title} required />
            <Select label="Tipo do imóvel" value={form.property_type} onChange={(e) => update('property_type', e.target.value)} error={errors.property_type}>
              {propertyTypes.map((type) => <option key={type} value={type}>{type}</option>)}
            </Select>
            <Input label="Endereço" value={form.address} onChange={(e) => update('address', e.target.value)} className="dossier-form-full" />
            <Input label="Bairro" value={form.neighborhood} onChange={(e) => update('neighborhood', e.target.value)} />
            <Input label="Cidade" value={form.city} onChange={(e) => update('city', e.target.value)} error={errors.city} required />
            <Input label="Estado (UF)" maxLength={2} value={form.state} onChange={(e) => update('state', e.target.value)} error={errors.state} required />
            <Input label="Área total (m²)" type="number" step="0.01" value={form.area_m2} onChange={(e) => update('area_m2', e.target.value)} error={errors.area_m2} />
            <Input label="Área privativa (m²)" type="number" step="0.01" value={form.private_area_m2} onChange={(e) => update('private_area_m2', e.target.value)} error={errors.private_area_m2} />
            <Input label="Quartos" type="number" value={form.bedrooms} onChange={(e) => update('bedrooms', e.target.value)} error={errors.bedrooms} />
            <Input label="Vagas de garagem" type="number" value={form.parking_spots} onChange={(e) => update('parking_spots', e.target.value)} error={errors.parking_spots} />
            <Textarea label="Descrição do imóvel (texto original da origem)" value={form.description} onChange={(e) => update('description', e.target.value)} className="dossier-form-full" />
            <p className="wizard-subtitle dossier-form-full">Identificação na origem</p>
            <Input label="Origem / instituição" placeholder="Ex.: Caixa Econômica Federal" value={form.origin} onChange={(e) => update('origin', e.target.value)} />
            <Input label="Número do imóvel na origem" value={form.origin_property_code} onChange={(e) => update('origin_property_code', e.target.value)} />
            <Input label="Número da inscrição" value={form.inscription} onChange={(e) => update('inscription', e.target.value)} />
            <Input label="Modalidade" placeholder="Ex.: Extrajudicial" value={form.modality} onChange={(e) => update('modality', e.target.value)} />
            <Input label="Sistema" placeholder="Ex.: SFI" value={form.system} onChange={(e) => update('system', e.target.value)} />
          </div>
        )}

        {step === 1 && (
          <div className="dossier-form wizard-form">
            <Input label="Valor de avaliação (R$)" type="number" step="0.01" value={form.appraisal_value} onChange={(e) => update('appraisal_value', e.target.value)} error={errors.appraisal_value} />
            <Input label="Leiloeiro" value={form.auctioneer} onChange={(e) => update('auctioneer', e.target.value)} />
            <p className="wizard-subtitle dossier-form-full">1º leilão</p>
            <Input label="Data do 1º leilão" type="datetime-local" value={form.first_auction_date} onChange={(e) => update('first_auction_date', e.target.value)} />
            <Input label="Valor do 1º leilão (R$)" type="number" step="0.01" value={form.first_auction_value} onChange={(e) => update('first_auction_value', e.target.value)} error={errors.first_auction_value} />
            <p className="wizard-subtitle dossier-form-full">2º leilão</p>
            <Input label="Data do 2º leilão" type="datetime-local" value={form.second_auction_date} onChange={(e) => update('second_auction_date', e.target.value)} />
            <Input label="Valor do 2º leilão (R$)" type="number" step="0.01" value={form.second_auction_value} onChange={(e) => update('second_auction_value', e.target.value)} error={errors.second_auction_value} />
            <p className="wizard-subtitle dossier-form-full">Edital</p>
            <Input label="Número do edital" placeholder="Ex.: 0044/0226 - CPA/RE" value={form.notice_identifier} onChange={(e) => update('notice_identifier', e.target.value)} />
            <Input label="Item do edital" value={form.notice_item} onChange={(e) => update('notice_item', e.target.value)} />
            <p className="wizard-subtitle dossier-form-full">Matrícula</p>
            <Input label="Número da matrícula" value={form.registration_number} onChange={(e) => update('registration_number', e.target.value)} />
            <Input label="Cartório / Ofício" value={form.registry_office} onChange={(e) => update('registry_office', e.target.value)} />
            <Input label="Comarca" value={form.registration_comarca} onChange={(e) => update('registration_comarca', e.target.value)} />
          </div>
        )}

        {step === 2 && (
          <div className="wizard-sources">
            <p className="wizard-hint">Informe as fontes oficiais usadas (página do imóvel, edital, matrícula). Opcional.</p>
            {sources.map((source, index) => (
              <Card key={index} padding="md" className="wizard-source-row">
                <Select label="Tipo" value={source.source_type} onChange={(e) => updateSource(index, { source_type: e.target.value as SourceType })}>
                  {(Object.keys(sourceTypeLabels) as SourceType[]).map((type) => <option key={type} value={type}>{sourceTypeLabels[type]}</option>)}
                </Select>
                <Input label="URL" placeholder="https://…" value={source.url} onChange={(e) => updateSource(index, { url: e.target.value })} error={errors[`source-${index}`]} />
                <Input label="Descrição" value={source.description} onChange={(e) => updateSource(index, { description: e.target.value })} />
                <Button variant="ghost" onClick={() => removeSource(index)} aria-label="Remover fonte"><Trash2 size={16} /> Remover</Button>
              </Card>
            ))}
            <Button variant="secondary" onClick={addSource}><Plus size={16} /> Adicionar fonte</Button>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-docs">
            <p className="wizard-hint">Anexe documentos (edital, matrícula, outros). O processamento acontece após o cadastro e não bloqueia a criação do imóvel.</p>
            <label className="wizard-dropzone">
              <Upload size={20} />
              <span>Selecionar arquivos</span>
              <input type="file" multiple onChange={(e) => onDocFiles(e.target.files)} style={{ display: 'none' }} />
            </label>
            {docs.map((doc, index) => (
              <Card key={index} padding="md" className="wizard-source-row">
                <span className="wizard-doc-name">{doc.file.name}</span>
                <Select label="Tipo" value={doc.document_type} onChange={(e) => updateDoc(index, e.target.value)}>
                  <option value="EDITAL">Edital</option>
                  <option value="MATRICULA">Matrícula</option>
                  <option value="OUTRO">Outro</option>
                </Select>
                <Button variant="ghost" onClick={() => removeDoc(index)} aria-label="Remover documento"><Trash2 size={16} /> Remover</Button>
              </Card>
            ))}
          </div>
        )}

        {step === 4 && (
          <div className="wizard-review">
            <ReviewBlock title="Identificação" lines={[form.title || 'Não informado', form.origin ? `Origem: ${form.origin}` : '', form.origin_property_code ? `Nº imóvel: ${form.origin_property_code}` : '']} />
            <ReviewBlock title="Localização" lines={[[form.city, form.state].filter(Boolean).join(' - ') || 'Não informado', form.neighborhood, form.address]} />
            <ReviewBlock title="Imóvel" lines={[form.property_type, form.bedrooms ? `${form.bedrooms} quarto(s)` : '', form.parking_spots ? `${form.parking_spots} vaga(s)` : '', form.area_m2 ? `${form.area_m2} m²` : '']} />
            <ReviewBlock title="Leilão" lines={[`Avaliação: ${money(form.appraisal_value)}`, `1º leilão: ${money(form.first_auction_value)}`, `2º leilão: ${money(form.second_auction_value)}`, form.auctioneer ? `Leiloeiro: ${form.auctioneer}` : '']} />
            <ReviewBlock title="Matrícula" lines={[form.registration_number, form.registry_office, form.registration_comarca]} />
            <ReviewBlock title="Edital" lines={[form.notice_identifier, form.notice_item ? `Item ${form.notice_item}` : '']} />
            <ReviewBlock title="Fontes" lines={sources.length ? sources.map((s) => `${sourceTypeLabels[s.source_type]}: ${s.url || s.description || '—'}`) : ['Nenhuma fonte informada']} />
            <ReviewBlock title="Documentos" lines={docs.length ? docs.map((d) => `${d.document_type}: ${d.file.name}`) : ['Nenhum documento anexado']} />
          </div>
        )}

        <div className="dossier-form-actions wizard-actions">
          {saveError && <Alert tone="danger">{saveError}</Alert>}
          {step > 0 && <Button variant="ghost" onClick={goBack} disabled={saving}>Voltar</Button>}
          {step < steps.length - 1 ? (
            <Button onClick={goNext}>Avançar</Button>
          ) : (
            <Button onClick={() => void handleSubmit()} loading={saving}>Salvar imóvel</Button>
          )}
        </div>
      </Section>
    </Card>
  )
}

function ReviewBlock({ title, lines }: { title: string; lines: (string | undefined)[] }) {
  const visible = lines.filter((line): line is string => Boolean(line && line.trim()))
  return (
    <div className="wizard-review-block">
      <p className="eyebrow">{title}</p>
      {visible.length ? visible.map((line, index) => <p key={index}>{line}</p>) : <p className="wizard-muted">Não informado</p>}
    </div>
  )
}
