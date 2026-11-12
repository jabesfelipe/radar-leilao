import { useState, type ReactNode } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { useBodyScrollLock } from './useBodyScrollLock'

type SessionUser = { id: number; email: string; name: string; role: string }

type LayoutProps = {
  currentPath: string
  onNavigate: (path: string) => void
  children: ReactNode
  user?: SessionUser | null
  onLogout?: () => void
}

export function Layout({ currentPath, onNavigate, children, user, onLogout }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // Menu aberto (só acontece no mobile): a página atrás do overlay não rola.
  useBodyScrollLock(sidebarOpen)

  const navigate = (path: string) => {
    onNavigate(path)
    setSidebarOpen(false)
  }

  return (
    <div className="app-shell">
      <Sidebar currentPath={currentPath} isOpen={sidebarOpen} onNavigate={navigate} onClose={() => setSidebarOpen(false)} />
      <div className="app-content">
        <Header onMenuClick={() => setSidebarOpen(true)} user={user} onLogout={onLogout} />
        <main>{children}</main>
      </div>
    </div>
  )
}
