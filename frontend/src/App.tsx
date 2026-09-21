import { useEffect, useState } from 'react'
import { ArrowRight, BarChart3, ClipboardCheck, FileText, ShieldCheck } from 'lucide-react'
import { Layout } from './components/Layout'
import { PageContainer } from './components/PageContainer'
import { navigationItems } from './components/Sidebar'

const defaultPath = '/dashboard'

function normalizePath(pathname: string) {
  return navigationItems.some((item) => item.path === pathname) ? pathname : defaultPath
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

  const page = navigationItems.find((item) => item.path === currentPath) ?? navigationItems[0]

  return (
    <Layout currentPath={currentPath} onNavigate={navigate}>
      <PageContainer title={page.label} description={pageDescription[page.path]}>
        <FoundationPage path={page.path} />
      </PageContainer>
    </Layout>
  )
}

const pageDescription: Record<string, string> = {
  '/dashboard': 'Visão geral da operação e dos módulos do Radar Leilão.',
  '/imoveis': 'Espaço reservado para a gestão dos imóveis monitorados.',
  '/documentos': 'Espaço reservado para documentos e rastreabilidade documental.',
  '/juridico': 'Espaço reservado para informações e acompanhamentos jurídicos.',
  '/financeiro': 'Espaço reservado para a visão financeira dos imóveis.',
  '/mercado': 'Espaço reservado para referências e análises de mercado.',
  '/ocupacao': 'Espaço reservado para informações de ocupação.',
  '/checklist': 'Espaço reservado para o Checklist Mestre.',
  '/riscos': 'Espaço reservado para riscos identificados e seu acompanhamento.',
  '/veredito': 'Espaço reservado para o veredito consolidado de cada análise.',
  '/historico': 'Espaço reservado para o histórico de análises e alterações.',
}

function FoundationPage({ path }: { path: string }) {
  if (path === '/dashboard') {
    return (
      <div className="foundation-grid">
        <div className="welcome-card">
          <div className="welcome-icon"><ShieldCheck size={24} /></div>
          <div>
            <p className="eyebrow">BASE OPERACIONAL</p>
            <h3>Seu radar está pronto para evoluir.</h3>
            <p>A fundação visual está organizada para receber os próximos módulos do produto.</p>
          </div>
        </div>
        <div className="foundation-card">
          <BarChart3 size={20} />
          <strong>11 módulos</strong>
          <span>Navegação principal configurada</span>
        </div>
        <div className="foundation-card">
          <ClipboardCheck size={20} />
          <strong>Interface em pt-BR</strong>
          <span>Identidade visual consistente</span>
        </div>
      </div>
    )
  }

  return (
    <div className="module-placeholder">
      <div className="placeholder-icon"><FileText size={24} /></div>
      <div>
        <p className="eyebrow">MÓDULO BASE</p>
        <h3>{navigationItems.find((item) => item.path === path)?.label}</h3>
        <p>Esta página define o ponto de entrada visual do módulo. Funcionalidades e dados serão adicionados em tarefas futuras.</p>
      </div>
      <span className="placeholder-arrow"><ArrowRight size={18} /></span>
    </div>
  )
}

export default App
