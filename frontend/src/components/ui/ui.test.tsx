import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Alert, Badge, Button, Card, EmptyState, IconButton, Input, LoadingState, Section, Select, Textarea } from './index'
import { Bell } from 'lucide-react'

describe('Design System Radar Leilão', () => {
  it('renderiza componentes de conteúdo e formulário com acessibilidade', () => {
    render(
      <div>
        <Badge tone="success">Ativo</Badge>
        <Card><Section title="Resumo" description="Descrição da seção">Conteúdo</Section></Card>
        <Input label="Nome" hint="Informe um nome" />
        <Select label="Categoria"><option value="base">Base</option></Select>
        <Textarea label="Observações" error="Campo obrigatório" />
        <EmptyState title="Nenhum item" description="Ainda não há conteúdo" />
        <LoadingState label="Carregando tela" />
        <Alert tone="warning" title="Atenção">Revise os dados.</Alert>
      </div>,
    )

    expect(screen.getByText('Ativo')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Resumo' })).toBeInTheDocument()
    expect(screen.getByLabelText('Nome')).toHaveAttribute('aria-describedby')
    expect(screen.getByLabelText('Categoria')).toBeInTheDocument()
    expect(screen.getByLabelText('Observações')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('status')).toHaveTextContent('Carregando tela')
    expect(screen.getByRole('alert')).toHaveTextContent('Revise os dados.')
  })

  it('mantém estados loading/disabled e dispara interação do Button', () => {
    const onClick = vi.fn()
    const { rerender } = render(<Button onClick={onClick}>Continuar</Button>)
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }))
    expect(onClick).toHaveBeenCalledOnce()

    rerender(<Button loading>Continuar</Button>)
    expect(screen.getByRole('button', { name: 'Carregando…' })).toBeDisabled()
  })

  it('expõe nome acessível e interação no IconButton', () => {
    const onClick = vi.fn()
    render(<IconButton label="Abrir notificações" icon={<Bell />} onClick={onClick} />)
    const button = screen.getByRole('button', { name: 'Abrir notificações' })
    fireEvent.click(button)
    expect(onClick).toHaveBeenCalledOnce()
  })
})
