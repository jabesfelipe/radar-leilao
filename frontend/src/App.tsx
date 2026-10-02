import { useEffect, useState } from 'react'
import { Layout } from './components/Layout'
import { PageContainer } from './components/PageContainer'
import { PropertiesPage } from './pages/PropertiesPage'
import { PropertyDetailPage } from './pages/PropertyDetailPage'
import { AuctioneersPage } from './pages/AuctioneersPage'
import {
  DashboardHub, FinancialHub, JuridicalHub, RisksHub, VerdictsHub,
  MarketHub, OccupancyHub, ChecklistHub, DocumentsHub, HistoryHub,
} from './pages/hubs'
import { navigationItems } from './components/Sidebar'

const defaultPath = '/dashboard'

const propertyDetailPattern = /^\/imoveis\/(\d+)$/

function normalizePath(pathname: string) {
  if (propertyDetailPattern.test(pathname)) return pathname
  return navigationItems.some((item) => item.path === pathname) ? pathname : defaultPath
}

function matchPropertyDetail(pathname: string): number | null {
  const match = propertyDetailPattern.exec(pathname)
  return match ? Number(match[1]) : null
}

function App() {
  const [currentPath, setCurrentPath] = useState(() => normalizePath(window.location.pathname))

  useEffect(() => {
    const handlePopState = () => setCurrentPath(normalizePath(window.location.pathname))
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigate = (path: string) => {
    if (path === currentPath) return
    window.history.pushState({}, '', path)
    setCurrentPath(path)
  }

  const openProperty = (id: number) => navigate(`/imoveis/${id}`)

  const detailPropertyId = matchPropertyDetail(currentPath)
  if (detailPropertyId !== null) {
    return (
      <Layout currentPath="/imoveis" onNavigate={navigate}>
        <PageContainer title="Detalhe do imóvel" description="Centro de navegação do imóvel e ponto de partida para as análises.">
          <PropertyDetailPage propertyId={detailPropertyId} onBack={() => navigate('/imoveis')} />
        </PageContainer>
      </Layout>
    )
  }

  const page = navigationItems.find((item) => item.path === currentPath) ?? navigationItems[0]

  return (
    <Layout currentPath={currentPath} onNavigate={navigate}>
      <PageContainer title={page.label} description={pageDescription[page.path] ?? ''}>
        <HubRouter path={page.path} onOpenProperty={openProperty} />
      </PageContainer>
    </Layout>
  )
}

const pageDescription: Record<string, string> = {
  '/dashboard': 'Painel de decisão: indicadores, pipeline e alertas calculados dos dados reais.',
  '/imoveis': 'Cadastre e acompanhe os imóveis que fazem parte do seu radar.',
  '/documentos': 'Central documental: todos os documentos do Radar, com filtros e rastreabilidade.',
  '/juridico': 'Central jurídica: processos, correlação e riscos consolidados.',
  '/financeiro': 'Central financeira: preço máximo, TCO, break-even, ROI e margem por imóvel.',
  '/mercado': 'Comparáveis de venda e aluguel reunidos por imóvel.',
  '/ocupacao': 'Situação de ocupação e impacto para a decisão.',
  '/checklist': 'Checklist Mestre consolidado por imóvel.',
  '/riscos': 'Riscos consolidados por severidade, com rastreabilidade à evidência.',
  '/veredito': 'Vereditos consolidados e seus indicadores de decisão.',
  '/historico': 'Linha do tempo global das ações e análises do Radar.',
  '/leiloeiros': 'Cadastro de leiloeiros, portais/acessos e documentos.',
}

function HubRouter({ path, onOpenProperty }: { path: string; onOpenProperty: (id: number) => void }) {
  switch (path) {
    case '/imoveis': return <PropertiesPage onOpenProperty={onOpenProperty} />
    case '/dashboard': return <DashboardHub onOpenProperty={onOpenProperty} />
    case '/documentos': return <DocumentsHub onOpenProperty={onOpenProperty} />
    case '/juridico': return <JuridicalHub onOpenProperty={onOpenProperty} />
    case '/financeiro': return <FinancialHub onOpenProperty={onOpenProperty} />
    case '/mercado': return <MarketHub onOpenProperty={onOpenProperty} />
    case '/ocupacao': return <OccupancyHub onOpenProperty={onOpenProperty} />
    case '/checklist': return <ChecklistHub onOpenProperty={onOpenProperty} />
    case '/riscos': return <RisksHub onOpenProperty={onOpenProperty} />
    case '/veredito': return <VerdictsHub onOpenProperty={onOpenProperty} />
    case '/historico': return <HistoryHub onOpenProperty={onOpenProperty} />
    case '/leiloeiros': return <AuctioneersPage />
    default: return <DashboardHub onOpenProperty={onOpenProperty} />
  }
}

export default App
