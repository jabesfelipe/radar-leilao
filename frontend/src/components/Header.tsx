import { Bell, Menu } from 'lucide-react'

type HeaderProps = {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="topbar">
      <button className="mobile-menu" type="button" onClick={onMenuClick} aria-label="Abrir menu">
        <Menu size={20} />
      </button>
      <div>
        <p className="topbar-kicker">RADAR LEILÃO</p>
        <h1>Central de análise patrimonial</h1>
      </div>
      <div className="topbar-actions">
        <button className="icon-button" type="button" aria-label="Notificações">
          <Bell size={18} />
        </button>
        <div className="user-badge" aria-label="Usuário atual">JC</div>
      </div>
    </header>
  )
}
