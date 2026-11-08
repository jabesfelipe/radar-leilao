import { Bell, LogOut, Menu } from 'lucide-react'
import { Button, IconButton } from './ui'

type SessionUser = { id: number; email: string; name: string; role: string }

type HeaderProps = {
  onMenuClick: () => void
  user?: SessionUser | null
  onLogout?: () => void
}

function initials(user?: SessionUser | null): string {
  const base = (user?.name || user?.email || '').trim()
  if (!base) return '—'
  const parts = base.split(/[\s@.]+/).filter(Boolean)
  return (parts[0]?.[0] ?? '').concat(parts[1]?.[0] ?? '').toUpperCase() || base[0].toUpperCase()
}

export function Header({ onMenuClick, user, onLogout }: HeaderProps) {
  return (
    <header className="topbar">
      <IconButton label="Abrir menu" icon={<Menu size={20} />} className="mobile-menu" onClick={onMenuClick} />
      <div>
        <p className="topbar-kicker">RADAR LEILÃO</p>
        <h1>Central de análise patrimonial</h1>
      </div>
      <div className="topbar-actions">
        <IconButton label="Notificações" icon={<Bell size={18} />} className="icon-button" />
        {user && (
          <span className="topbar-user" title={`${user.email} · ${user.role}`}>
            <span className="user-badge" aria-label="Usuário atual">{initials(user)}</span>
            <span className="topbar-user-meta"><strong>{user.name || user.email}</strong><small>{user.role}</small></span>
          </span>
        )}
        {onLogout && (
          <Button variant="ghost" size="sm" onClick={onLogout} aria-label="Sair"><LogOut size={16} /> Sair</Button>
        )}
      </div>
    </header>
  )
}
