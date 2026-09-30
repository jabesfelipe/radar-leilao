import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Coins, Plus, RefreshCw, Target, Wallet } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section, Select } from '../components/ui'
import {
  createCost, createDebt, formatMoney, formatPercent, getFinance, listCosts, listDebts, saveFinanceAssumptions,
  type Cost, type Debt, type FinanceAssumptions, type FinanceResult,
} from '../services/finance'

type FinancialSectionProps = {
  propertyId: number
}

type CostForm = { category: string; description: string; amount: string; recurring: boolean }
type DebtForm = { category: string; creditor: string; amount: string; reference_date: string; status: string }

const initialCost: CostForm = { category: '', description: '', amount: '', recurring: false }
const initialDebt: DebtForm = { category: '', creditor: '', amount: '', reference_date: '', status: '' }

type AssumptionsForm = {
  goal_kind: '' | 'LUCRO_MINIMO' | 'MARGEM_MINIMA' | 'ROI_MINIMO'
  goal_value: string
  corretagem_pct: string
  tributo_pct: string
  tax_base: 'GANHO' | 'VENDA'
  valor_venda_estimado: string
  prazo_meses: string
  carregamento_mensal: string
}

const initialAssumptions: AssumptionsForm = {
  goal_kind: '', goal_value: '', corretagem_pct: '', tributo_pct: '', tax_base: 'GANHO',
  valor_venda_estimado: '', prazo_meses: '', carregamento_mensal: '',
}

// Percentuais são exibidos ao usuário em % (5 = 5%) e convertidos para fração na API.
function mergeAssumptions(p: FinanceAssumptions): AssumptionsForm {
  const pct = (v?: number | null) => (v === null || v === undefined ? '' : String(v * 100))
  const num = (v?: number | null) => (v === null || v === undefined ? '' : String(v))
  return {
    goal_kind: (p.goal_kind as AssumptionsForm['goal_kind']) || '',
    goal_value: p.goal_kind === 'LUCRO_MINIMO' ? num(p.goal_value) : pct(p.goal_value),
    corretagem_pct: pct(p.corretagem_pct),
    tributo_pct: pct(p.tributo_pct),
    tax_base: p.tax_base || 'GANHO',
    valor_venda_estimado: num(p.valor_venda_estimado),
    prazo_meses: p.prazo_meses == null ? '' : String(p.prazo_meses),
    carregamento_mensal: num(p.carregamento_mensal),
  }
}

function numOrNull(v: string): number | null {
  const t = v.trim()
  if (!t) return null
  const n = Number(t)
  return Number.isNaN(n) ? null : n
}
function intOrNull(v: string): number | null {
  const n = numOrNull(v)
  return n === null ? null : Math.trunc(n)
}
// Converte % informado (5) para fração (0.05) esperada pela API.
function pctOrNull(v: string): number | null {
  const n = numOrNull(v)
  return n === null ? null : n / 100
}

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

  // Premissas financeiras e resultado (Task 3).
  const [result, setResult] = useState<FinanceResult | null>(null)
  const [assumptions, setAssumptions] = useState<AssumptionsForm>(initialAssumptions)
  const [savingAssumptions, setSavingAssumptions] = useState(false)
  const [assumptionsError, setAssumptionsError] = useState('')
  const [assumptionsFeedback, setAssumptionsFeedback] = useState('')

  const loadFinance = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [loadedCosts, loadedDebts, finance] = await Promise.all([listCosts(propertyId), listDebts(propertyId), getFinance(propertyId)])
      setCosts(loadedCosts)
      setDebts(loadedDebts)
      setResult(finance.financeiro)
      if (finance.premissas) setAssumptions(mergeAssumptions(finance.premissas))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os dados financeiros.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  const submitAssumptions = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSavingAssumptions(true)
    setAssumptionsError('')
    setAssumptionsFeedback('')
    try {
      // LUCRO_MINIMO é em R$; MARGEM/ROI são percentuais informados em % -> fração.
      const goalValue = assumptions.goal_kind === 'LUCRO_MINIMO'
        ? numOrNull(assumptions.goal_value)
        : pctOrNull(assumptions.goal_value)
      const payload: FinanceAssumptions = {
        goal_kind: assumptions.goal_kind || null,
        goal_value: assumptions.goal_kind ? goalValue : null,
        corretagem_pct: pctOrNull(assumptions.corretagem_pct),
        tributo_pct: pctOrNull(assumptions.tributo_pct),
        tax_base: assumptions.tax_base,
        valor_venda_estimado: numOrNull(assumptions.valor_venda_estimado),
        prazo_meses: intOrNull(assumptions.prazo_meses),
        carregamento_mensal: numOrNull(assumptions.carregamento_mensal),
      }
      const finance = await saveFinanceAssumptions(propertyId, payload)
      setResult(finance.financeiro)
      setAssumptionsFeedback('Premissas financeiras salvas. O resultado foi recalculado.')
    } catch (cause) {
      setAssumptionsError(cause instanceof Error ? cause.message : 'Não foi possível salvar as premissas.')
    } finally {
      setSavingAssumptions(false)
    }
  }

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

  const goalLabel = assumptions.goal_kind === 'LUCRO_MINIMO' ? 'Meta de lucro (R$)'
    : assumptions.goal_kind === 'MARGEM_MINIMA' ? 'Meta de margem (%)'
    : assumptions.goal_kind === 'ROI_MINIMO' ? 'Meta de ROI (%)' : 'Valor/percentual da meta'

  return (
    <div className="financial-section">
      <Section title="Premissas e resultado" description="Informe as premissas para calcular o resultado líquido e o preço máximo de arrematação." className="dossier-section">
        <Card variant="elevated" padding="lg" className="dossier-form-card">
          <form className="dossier-form" onSubmit={submitAssumptions} noValidate>
            <Select label="Meta financeira" value={assumptions.goal_kind} onChange={(e) => setAssumptions((a) => ({ ...a, goal_kind: e.target.value as AssumptionsForm['goal_kind'] }))}>
              <option value="">Não definida</option>
              <option value="LUCRO_MINIMO">Lucro mínimo (R$)</option>
              <option value="MARGEM_MINIMA">Margem mínima (%)</option>
              <option value="ROI_MINIMO">ROI mínimo (%)</option>
            </Select>
            <Input label={goalLabel} type="number" step="0.01" value={assumptions.goal_value} onChange={(e) => setAssumptions((a) => ({ ...a, goal_value: e.target.value }))} disabled={!assumptions.goal_kind} />
            <Input label="Valor de venda estimado (R$)" type="number" step="0.01" value={assumptions.valor_venda_estimado} onChange={(e) => setAssumptions((a) => ({ ...a, valor_venda_estimado: e.target.value }))} />
            <Input label="Corretagem na venda (%)" type="number" step="0.01" value={assumptions.corretagem_pct} onChange={(e) => setAssumptions((a) => ({ ...a, corretagem_pct: e.target.value }))} />
            <Input label="Tributo na venda (%)" type="number" step="0.01" value={assumptions.tributo_pct} onChange={(e) => setAssumptions((a) => ({ ...a, tributo_pct: e.target.value }))} />
            <Select label="Base do tributo" value={assumptions.tax_base} onChange={(e) => setAssumptions((a) => ({ ...a, tax_base: e.target.value as 'GANHO' | 'VENDA' }))}>
              <option value="GANHO">Sobre o ganho (venda − custo total)</option>
              <option value="VENDA">Sobre o valor de venda</option>
            </Select>
            <Input label="Prazo da operação (meses)" type="number" step="1" value={assumptions.prazo_meses} onChange={(e) => setAssumptions((a) => ({ ...a, prazo_meses: e.target.value }))} />
            <Input label="Carregamento mensal (R$/mês)" type="number" step="0.01" value={assumptions.carregamento_mensal} onChange={(e) => setAssumptions((a) => ({ ...a, carregamento_mensal: e.target.value }))} />
            <div className="dossier-form-actions">
              {assumptionsError && <Alert tone="danger">{assumptionsError}</Alert>}
              {assumptionsFeedback && <Alert tone="success">{assumptionsFeedback}</Alert>}
              <Button type="submit" loading={savingAssumptions}><Target size={16} /> Salvar premissas e recalcular</Button>
            </div>
          </form>
        </Card>
        {result && (
          <Card padding="lg" className="finance-result">
            <dl className="dossier-facts">
              <Fact label="Custo total" value={formatMoney(result.custo_total as number)} />
              <Fact label="Custo de saída" value={formatMoney(result.custo_saida as number)} />
              <Fact label="Valor de venda" value={formatMoney(result.valor_mercado as number)} />
              <Fact label="Resultado líquido" value={formatMoney(result.resultado_liquido as number)} />
              <Fact label="Margem líquida" value={formatPercent(result.margem_liquida as number)} />
              <Fact label="ROI da operação" value={formatPercent(result.roi_operacao as number)} />
              <Fact label="Preço máximo de arrematação" value={formatMoney(result.preco_maximo as number)} />
            </dl>
            {result.resultado_provisorio && (
              <Alert tone="warning" title="Resultado provisório">Há custos materiais ainda desconhecidos. Este resultado é uma simulação parcial, não um valor validado.</Alert>
            )}
            {result.preco_maximo == null && (
              <Alert tone="info" title="Preço máximo indisponível">
                {result.preco_maximo_detalhe?.mensagem || 'Informe a meta e o valor de venda estimado para calcular o preço máximo.'}
              </Alert>
            )}
            {Array.isArray(result.pendencias) && result.pendencias.length > 0 && (
              <div className="finance-pendencias">
                <strong>Pendências financeiras</strong>
                <ul>{result.pendencias.map((p, i) => <li key={i}>{p}</li>)}</ul>
              </div>
            )}
          </Card>
        )}
      </Section>

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
