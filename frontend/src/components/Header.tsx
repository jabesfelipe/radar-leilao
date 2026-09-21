import { Bell, Menu } from 'lucide-react'
import { IconButton } from './ui'

type HeaderProps = {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="topbar">
      <IconButton label="Abrir menu" icon={<Menu size={20} />} className="mobile-menu" onClick={onMenuClick} />
      <div>
        <p className="topbar-kicker">RADAR LEILÃO</p>
        <h1>Central de análise patrimonial</h1>
      </div>
      <div className="topbar-actions">
        <IconButton label="Notificações" icon={<Bell size={18} />} className="icon-button" />
        <div className="user-badge" aria-label="Usuário atual">JC</div>
      </div>
    </header>
  )
}
