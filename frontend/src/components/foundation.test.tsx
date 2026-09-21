import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Layout } from './Layout'
import { Sidebar } from './Sidebar'

describe('foundation responsiva e navegação', () => {
  it('renderiza a marca, módulos e chama navegação da Sidebar', () => {
    const onNavigate = vi.fn()
    render(<Sidebar currentPath="/dashboard" isOpen={false} onNavigate={onNavigate} onClose={vi.fn()} />)

    expect(screen.getByText('RADAR')).toBeInTheDocument()
    expect(screen.getByText('LEILÃO')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dashboard' })).toHaveClass('navigation-item-active')
    fireEvent.click(screen.getByRole('button', { name: 'Imóveis' }))
    expect(onNavigate).toHaveBeenCalledWith('/imoveis')
  })

  it('abre e fecha o menu mobile pela mesma implementação do Layout', () => {
    render(<Layout currentPath="/dashboard" onNavigate={vi.fn()}><p>Conteúdo</p></Layout>)

    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    const closeButtons = screen.getAllByRole('button', { name: 'Fechar menu' })
    expect(closeButtons).toHaveLength(2)
    expect(document.querySelector('.sidebar')).toHaveClass('sidebar-open')
    fireEvent.click(closeButtons[1])
    expect(document.querySelector('.sidebar')).not.toHaveClass('sidebar-open')
    expect(document.querySelector('.sidebar-overlay')).not.toBeInTheDocument()
  })
})
