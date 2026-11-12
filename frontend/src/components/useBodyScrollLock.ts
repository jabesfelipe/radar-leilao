import { useEffect } from 'react'

/**
 * Trava a rolagem da página enquanto `active` for true (ex.: menu lateral aberto no mobile).
 *
 * `overflow: hidden` no body não basta no Safari iOS anterior ao 16: o documento continua
 * rolando por baixo do overlay. A técnica robusta é fixar o body na posição atual
 * (`position: fixed; top: -scrollY`) e restaurar o scroll ao destravar. A rolagem do
 * próprio menu não é afetada (ela acontece no contêiner interno, não no documento).
 */
export function useBodyScrollLock(active: boolean) {
  useEffect(() => {
    if (!active || typeof document === 'undefined') return
    const { body } = document
    const scrollY = window.scrollY || window.pageYOffset || 0
    const previous = {
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      right: body.style.right,
      width: body.style.width,
      overflow: body.style.overflow,
    }
    body.style.position = 'fixed'
    body.style.top = `-${scrollY}px`
    body.style.left = '0'
    body.style.right = '0'
    body.style.width = '100%'
    body.style.overflow = 'hidden'
    body.classList.add('scroll-locked')
    return () => {
      Object.assign(body.style, previous)
      body.classList.remove('scroll-locked')
      // No topo (scrollY 0) o body destravado já está na posição certa.
      if (scrollY) window.scrollTo(0, scrollY)
    }
  }, [active])
}
