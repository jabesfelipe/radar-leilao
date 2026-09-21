import { LayoutDashboard, Building2, FileText, Scale, Wallet, BarChart3, Home, ClipboardCheck, ShieldAlert, BadgeCheck, History, X } from 'lucide-react'
import { IconButton } from './ui'

type NavigationItem = {
  path: string
  label: string
  icon: typeof LayoutDashboard
}

export const navigationItems: NavigationItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/imoveis', label: 'Imóveis', icon: Building2 },
  { path: '/documentos', label: 'Documentos', icon: FileText },
  { path: '/juridico', label: 'Jurídico', icon: Scale },
  { path: '/financeiro', label: 'Financeiro', icon: Wallet },
  { path: '/mercado', label: 'Mercado', icon: BarChart3 },
  { path: '/ocupacao', label: 'Ocupação', icon: Home },
  { path: '/checklist', label: 'Checklist', icon: ClipboardCheck },
  { path: '/riscos', label: 'Riscos', icon: ShieldAlert },
  { path: '/veredito', label: 'Veredito', icon: BadgeCheck },
  { path: '/historico', label: 'Histórico', icon: History },
]

type SidebarProps = {
  currentPath: string
  isOpen: boolean
  onNavigate: (path: string) => void
  onClose: () => void
}

export function Sidebar({ currentPath, isOpen, onNavigate, onClose }: SidebarProps) {
  return (
    <>
      {isOpen && <button className="sidebar-overlay" type="button" onClick={onClose} aria-label="Fechar menu" />}
      <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark" aria-hidden="true"><span /></div>
          <div>
            <strong>RADAR</strong>
            <span>LEILÃO</span>
          </div>
          <IconButton label="Fechar menu" icon={<X size={18} />} className="close-menu" onClick={onClose} />
        </div>
        <p className="navigation-title">MÓDULOS PRINCIPAIS</p>
        <nav className="navigation" aria-label="Navegação principal">
          {navigationItems.map(({ path, label, icon: Icon }) => (
            <button
              className={`navigation-item ${currentPath === path ? 'navigation-item-active' : ''}`}
              key={path}
              type="button"
              onClick={() => onNavigate(path)}
            >
              <Icon size={17} strokeWidth={currentPath === path ? 2.3 : 1.8} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot" />
          <div>
            <strong>Ambiente local</strong>
            <small>Fundação v0.1</small>
          </div>
        </div>
      </aside>
    </>
  )
}
