import { useState, type ReactNode } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

type LayoutProps = {
  currentPath: string
  onNavigate: (path: string) => void
  children: ReactNode
}

export function Layout({ currentPath, onNavigate, children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const navigate = (path: string) => {
    onNavigate(path)
    setSidebarOpen(false)
  }

  return (
    <div className="app-shell">
      <Sidebar currentPath={currentPath} isOpen={sidebarOpen} onNavigate={navigate} onClose={() => setSidebarOpen(false)} />
      <div className="app-content">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main>{children}</main>
      </div>
    </div>
  )
}
