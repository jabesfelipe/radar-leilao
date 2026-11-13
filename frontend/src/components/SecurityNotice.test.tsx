import { act, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SecurityNotice } from './SecurityNotice'

describe('SecurityNotice', () => {
  it('não renderiza nada sem eventos', () => {
    const { container } = render(<SecurityNotice />)
    expect(container).toBeEmptyDOMElement()
  })

  it('mostra aviso acessível em 403 e permite fechar', () => {
    render(<SecurityNotice />)
    act(() => { window.dispatchEvent(new CustomEvent('radar:forbidden')) })
    expect(screen.getByRole('alert')).toHaveTextContent(/não tem permissão/i)
    act(() => { screen.getByRole('button', { name: /fechar mensagem/i }).click() })
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('mostra aviso de limite em 429', () => {
    render(<SecurityNotice />)
    act(() => { window.dispatchEvent(new CustomEvent('radar:rate-limited')) })
    expect(screen.getByRole('alert')).toHaveTextContent(/aguarde um instante/i)
  })
})
