'use client'

import { ReactNode } from 'react'

interface CartProviderProps {
  children: ReactNode
}

export default function CartProvider({ children }: CartProviderProps) {
  return <>{children}</>
}