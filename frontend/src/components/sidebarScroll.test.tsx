import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import css from '../styles.css?raw'
import { Layout } from './Layout'
import { Sidebar, navigationItems } from './Sidebar'

/** Corpo do primeiro bloco `@media (max-width: 680px)` que define a regra `.sidebar`. */
function mobileSidebarBlock(source: string): string {
  const start = source.search(/@media \(max-width: 680px\) \{\s*\/\* Painel/)
  expect(start, 'bloco mobile do menu não encontrado em styles.css').toBeGreaterThan(-1)
  let depth = 0
  for (let i = source.indexOf('{', start); i < source.length; i++) {
    if (source[i] === '{') depth++
    if (source[i] === '}') { depth--; if (depth === 0) return source.slice(start, i + 1) }
  }
  throw new Error('bloco mobile não fechado')
}

function rule(block: string, selector: string): string {
  const m = block.match(new RegExp(`\\n\\s*${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')} \\{([^}]*)\\}`))
  expect(m, `regra ${selector} não encontrada`).not.toBeNull()
  return m![1]
}

describe('menu lateral: estrutura rolável', () => {
  it('cabeçalho fica fora da área rolável e TODOS os itens (inclusive Administração) ficam dentro dela', () => {
    render(<Sidebar currentPath="/administracao" isOpen onNavigate={vi.fn()} onClose={vi.fn()} />)
    const aside = document.querySelector('aside.sidebar') as HTMLElement
    const scroll = screen.getByTestId('sidebar-scroll')
    const header = aside.querySelector('.brand-row') as HTMLElement

    // ordem: cabeçalho e depois área rolável, ambos filhos diretos do painel
    expect(header.parentElement).toBe(aside)
    expect(scroll.parentElement).toBe(aside)
    expect(header.compareDocumentPosition(scroll) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(scroll.contains(header)).toBe(false)
    expect(within(header).getByRole('button', { name: 'Fechar menu' })).toBeInTheDocument()

    const nav = within(scroll).getByRole('navigation', { name: 'Navegação principal' })
    const labels = within(nav).getAllByRole('button').map((b) => b.textContent)
    expect(labels).toEqual(navigationItems.map((i) => i.label))
    expect(labels[labels.length - 1]).toBe('Administração')

    // destaque do módulo atual preservado
    const admin = within(nav).getByRole('button', { name: 'Administração' })
    expect(admin).toHaveClass('navigation-item-active')
    expect(admin).toHaveAttribute('aria-current', 'page')
    expect(scroll.querySelector('.sidebar-footer')).not.toBeNull()
  })
})

describe('menu lateral: CSS mobile (Safari iOS / iPhone 8 375×667)', () => {
  const mobile = mobileSidebarBlock(css)

  it('painel com altura da viewport e sem estourar: vh de fallback, top/bottom e overflow hidden', () => {
    const sidebar = rule(mobile, '.sidebar')
    expect(sidebar).toMatch(/position:\s*fixed/)
    expect(sidebar).toMatch(/top:\s*0/)
    expect(sidebar).toMatch(/bottom:\s*0/)
    expect(sidebar).toMatch(/max-height:\s*100vh/)
    expect(sidebar).toMatch(/overflow:\s*hidden/)
    expect(sidebar).toMatch(/env\(safe-area-inset-top/)
    expect(sidebar).toMatch(/env\(safe-area-inset-bottom/)
  })

  it('usa 100dvh quando suportado', () => {
    expect(css).toMatch(/@supports \(height: 100dvh\) \{\s*@media \(max-width: 680px\) \{\s*\.sidebar \{[^}]*height:\s*100dvh/)
  })

  it('área interna rola: min-height 0 (flex), overflow-y auto, touch scrolling e sem vazar o gesto', () => {
    const scroll = rule(mobile, '.sidebar-scroll')
    expect(scroll).toMatch(/min-height:\s*0/)
    expect(scroll).toMatch(/overflow-y:\s*auto/)
    expect(scroll).toMatch(/-webkit-overflow-scrolling:\s*touch/)
    expect(scroll).toMatch(/overscroll-behavior:\s*contain/)
    expect(rule(mobile, '.sidebar-overlay')).toMatch(/touch-action:\s*none/)
  })

  it('desktop: área rolável só preenche a coluna (sem overflow próprio) e o cabeçalho não encolhe', () => {
    const desktop = css.slice(0, css.indexOf('@media'))
    const scroll = rule(desktop, '.sidebar-scroll')
    expect(scroll).toMatch(/flex:\s*1 1 auto/)
    expect(scroll).not.toMatch(/overflow/)
    expect(rule(desktop, '.brand-row')).toMatch(/flex-shrink:\s*0/)
    expect(rule(desktop, '.sidebar')).not.toMatch(/position|overflow|height/)
  })
})

describe('menu lateral: trava da página atrás do menu', () => {
  let scrollTo: ReturnType<typeof vi.spyOn>
  beforeEach(() => {
    scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 420 })
  })
  afterEach(() => {
    scrollTo.mockRestore()
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 0 })
    document.body.removeAttribute('style')
  })

  it('abrir trava o body na posição atual; fechar pelo X destrava e restaura o scroll', () => {
    render(<Layout currentPath="/dashboard" onNavigate={vi.fn()}><p>Conteúdo</p></Layout>)
    expect(document.body.style.position).toBe('')

    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    expect(document.body.style.position).toBe('fixed')
    expect(document.body.style.top).toBe('-420px')
    expect(document.body.style.overflow).toBe('hidden')
    expect(document.body).toHaveClass('scroll-locked')

    const [, closeX] = screen.getAllByRole('button', { name: 'Fechar menu' })
    fireEvent.click(closeX)
    expect(document.querySelector('.sidebar')).not.toHaveClass('sidebar-open')
    expect(document.body.style.position).toBe('')
    expect(document.body.style.top).toBe('')
    expect(document.body).not.toHaveClass('scroll-locked')
    expect(scrollTo).toHaveBeenCalledWith(0, 420)
  })

  it('fechar pelo overlay também destrava', () => {
    render(<Layout currentPath="/dashboard" onNavigate={vi.fn()}><p>Conteúdo</p></Layout>)
    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    fireEvent.click(document.querySelector('.sidebar-overlay') as HTMLElement)
    expect(document.querySelector('.sidebar-overlay')).not.toBeInTheDocument()
    expect(document.body.style.position).toBe('')
  })

  it('navegar até o último item (Administração) chama a rota, fecha o menu e destrava a página', () => {
    const onNavigate = vi.fn()
    render(<Layout currentPath="/dashboard" onNavigate={onNavigate}><p>Conteúdo</p></Layout>)
    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    const scroll = screen.getByTestId('sidebar-scroll')
    fireEvent.click(within(scroll).getByRole('button', { name: 'Administração' }))
    expect(onNavigate).toHaveBeenCalledWith('/administracao')
    expect(document.querySelector('.sidebar')).not.toHaveClass('sidebar-open')
    expect(document.body.style.position).toBe('')
  })
})
