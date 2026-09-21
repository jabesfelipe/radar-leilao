import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Coins, Plus, RefreshCw, Wallet } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import { createCost, createDebt, formatMoney, listCosts, listDebts, type Cost, type Debt } from '../services/finance'

type FinancialSectionProps = {
  propertyId: number
}

type CostForm = { category: string; description: string; amount: string; recurring: boolean }
type DebtForm = { category: string; creditor: string; amount: string; reference_date: string; status: string }

const initialCost: CostForm = { category: '', description: '', amount: '', recurring: false }
const initialDebt: DebtForm = { category: '', creditor: '', amount: '', reference_date: '', status: '' }

function formatDate(value?: string | null) {
  if (!value) return 'Não informada'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR')
}

export function FinancialSection({ propertyId }: FinancialSectionProps) {
  const [costs, setCosts] = useState<Cost[]>([])
  const [debts, setDebts] = useState<Debt[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [costOpen, setCostOpen] = useState(false)
  const [costForm, setCostForm] = useState<CostForm>(initialCost)
  const [costErrors, setCostErrors] = useState<{ category?: string; description?: string }>({})
  const [savingCost, setSavingCost] = useState(false)
  const [costFeedback, setCostFeedback] = useState('')
  const [costError, setCostError] = useState('')

  const [debtOpen, setDebtOpen] = useState(false)
  const [debtForm, setDebtForm] = useState<DebtForm>(initialDebt)
  const [debtErrors, setDebtErrors] = useState<{ category?: string }>({})
  const [savingDebt, setSavingDebt] = useState(false)
  const [debtFeedback, setDebtFeedback] = useState('')
  const [debtError, setDebtError] = useState('')

  const loadFinance = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [loadedCosts, loadedDebts] = await Promise.all([listCosts(propertyId), listDebts(propertyId)])
      setCosts(loadedCosts)
      setDebts(loadedDebts)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os dados financeiros.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadFinance() }, [loadFinance])

  const submitCost = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const errors: { category?: string; description?: string } = {}
    if (!costForm.category.trim()) errors.category = 'Informe a categoria.'
    if (!costForm.description.trim()) errors.description = 'Informe a descrição.'
    setCostErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSavingCost(true)
    setCostError('')
    setCostFeedback('')
    try {
      const created = await createCost(propertyId, {
        category: costForm.category.trim(),
        description: costForm.description.trim(),
        amount: costForm.amount.trim() ? Number(costForm.amount) : undefined,
        recurring: costForm.recurring,
      })
      setCosts((current) => [...current, created])
      setCostOpen(false)
      setCostForm(initialCost)
      setCostFeedback('Custo cadastrado com sucesso.')
    } catch (cause) {
      setCostError(cause instanceof Error ? cause.message : 'Não foi possível cadastrar o custo.')
    } finally {
      setSavingCost(false)
    }
  }

  const submitDebt = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const errors: { category?: string } = {}
    if (!debtForm.category.trim()) errors.category = 'Informe a categoria.'
    setDebtErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSavingDebt(true)
    setDebtError('')
    setDebtFeedback('')
    try {
      const created = await createDebt(propertyId, {
        category: debtForm.category.trim(),
        creditor: debtForm.creditor.trim() || undefined,
        amount: debtForm.amount.trim() ? Number(debtForm.amount) : undefined,
        reference_date: debtForm.reference_date || undefined,
        status: debtForm.status.trim() || undefined,
      })
      setDebts((current) => [...current, created])
      setDebtOpen(false)
      setDebtForm(initialDebt)
      setDebtFeedback('Dívida cadastrada com sucesso.')
    } catch (cause) {
      setDebtError(cause instanceof Error ? cause.message : 'Não foi possível cadastrar a dívida.')
    } finally {
      setSavingDebt(false)
    }
  }

  if (loading) return <Section title="Financeiro" description="Custos e dívidas cadastrados para o imóvel." className="dossier-section"><LoadingState label="Carregando dados financeiros…" /></Section>

  if (error) {
    return (
      <Section title="Financeiro" description="Custos e dívidas cadastrados para o imóvel." className="dossier-section">
        <Card padding="lg" className="dossier-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadFinance()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      </Section>
    )
  }

  return (
    <div className="financial-section">
      <Section title="Custos" description="Custos relacionados ao imóvel." className="dossier-section" actions={<Button onClick={() => { setCostForm(initialCost); setCostErrors({}); setCostError(''); setCostFeedback(''); setCostOpen(true) }}><Plus size={16} /> Novo custo</Button>}>
        {costFeedback && <Alert tone="success" title="Cadastro concluído" className="dossier-feedback">{costFeedback}</Alert>}
        {costOpen && (
          <Card variant="elevated" padding="lg" className="dossier-form-card">
            <form className="dossier-form" onSubmit={submitCost} noValidate>
              <Input label="Categoria" value={costForm.category} onChange={(event) => { setCostForm((c) => ({ ...c, category: event.target.value })); setCostErrors((e) => ({ ...e, category: undefined })); setCostError('') }} error={costErrors.category} required />
              <Input label="Descrição" value={costForm.description} onChange={(event) => { setCostForm((c) => ({ ...c, description: event.target.value })); setCostErrors((e) => ({ ...e, description: undefined })); setCostError('') }} error={costErrors.description} required />
              <Input label="Valor (opcional)" type="number" step="0.01" value={costForm.amount} onChange={(event) => setCostForm((c) => ({ ...c, amount: event.target.value }))} />
              <label className="finance-check">
                <input type="checkbox" checked={costForm.recurring} onChange={(event) => setCostForm((c) => ({ ...c, recurring: event.target.checked }))} />
                <span>Custo recorrente</span>
              </label>
              <div className="dossier-form-actions">
                {costError && <Alert tone="danger">{costError}</Alert>}
                <Button variant="ghost" type="button" onClick={() => setCostOpen(false)} disabled={savingCost}>Cancelar</Button>
                <Button type="submit" loading={savingCost}>Salvar custo</Button>
              </div>
            </form>
          </Card>
        )}
        {costs.length === 0 ? (
          <Card padding="none"><EmptyState title="Nenhum custo cadastrado" description="Cadastre custos para compor a visão financeira do imóvel." icon={<Coins size={24} />} action={<Button onClick={() => setCostOpen(true)}><Plus size={16} /> Novo custo</Button>} /></Card>
        ) : (
          <div className="finance-list">
            {costs.map((cost) => (
              <Card key={cost.id} padding="md" className="finance-card">
                <div className="finance-card-head">
                  <strong>{cost.description}</strong>
                  {cost.recurring && <Badge tone="info" size="sm">Recorrente</Badge>}
                </div>
                <div className="finance-card-meta">
                  <span>{cost.category}</span>
                  <strong>{formatMoney(cost.amount)}</strong>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Section>

      <Section title="Dívidas" description="Dívidas e ônus relacionados ao imóvel." className="dossier-section" actions={<Button onClick={() => { setDebtForm(initialDebt); setDebtErrors({}); setDebtError(''); setDebtFeedback(''); setDebtOpen(true) }}><Plus size={16} /> Nova dívida</Button>}>
        {debtFeedback && <Alert tone="success" title="Cadastro concluído" className="dossier-feedback">{debtFeedback}</Alert>}
        {debtOpen && (
          <Card variant="elevated" padding="lg" className="dossier-form-card">
            <form className="dossier-form" onSubmit={submitDebt} noValidate>
              <Input label="Categoria" value={debtForm.category} onChange={(event) => { setDebtForm((d) => ({ ...d, category: event.target.value })); setDebtErrors({}); setDebtError('') }} error={debtErrors.category} required />
              <Input label="Credor (opcional)" value={debtForm.creditor} onChange={(event) => setDebtForm((d) => ({ ...d, creditor: event.target.value }))} />
              <Input label="Valor (opcional)" type="number" step="0.01" value={debtForm.amount} onChange={(event) => setDebtForm((d) => ({ ...d, amount: event.target.value }))} />
              <Input label="Data de referência (opcional)" type="date" value={debtForm.reference_date} onChange={(event) => setDebtForm((d) => ({ ...d, reference_date: event.target.value }))} />
              <Input label="Status (opcional)" value={debtForm.status} onChange={(event) => setDebtForm((d) => ({ ...d, status: event.target.value }))} placeholder="Ex.: PENDENTE" />
              <div className="dossier-form-actions">
                {debtError && <Alert tone="danger">{debtError}</Alert>}
                <Button variant="ghost" type="button" onClick={() => setDebtOpen(false)} disabled={savingDebt}>Cancelar</Button>
                <Button type="submit" loading={savingDebt}>Salvar dívida</Button>
              </div>
            </form>
          </Card>
        )}
        {debts.length === 0 ? (
          <Card padding="none"><EmptyState title="Nenhuma dívida cadastrada" description="Cadastre dívidas e ônus vinculados ao imóvel." icon={<Wallet size={24} />} action={<Button onClick={() => setDebtOpen(true)}><Plus size={16} /> Nova dívida</Button>} /></Card>
        ) : (
          <div className="finance-list">
            {debts.map((debt) => (
              <Card key={debt.id} padding="md" className="finance-card">
                <div className="finance-card-head">
                  <strong>{debt.category}</strong>
                  {debt.status && <Badge tone="warning" size="sm">{debt.status}</Badge>}
                </div>
                <dl className="dossier-facts">
                  <Fact label="Credor" value={debt.creditor} />
                  <Fact label="Valor" value={formatMoney(debt.amount)} />
                  <Fact label="Referência" value={formatDate(debt.reference_date)} />
                  {debt.evidence_id != null && <Fact label="Evidência" value={`#${debt.evidence_id}`} />}
                </dl>
              </Card>
            ))}
          </div>
        )}
      </Section>
    </div>
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
