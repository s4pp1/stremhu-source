import type { PropsWithChildren } from 'react'

import { AppFooter } from './app-footer'
import { AppHeader } from './app-header'

export function AppLayout(props: PropsWithChildren) {
  const { children } = props

  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader />
      <div className="flex-1 container mx-auto max-w-3xl py-8 px-4">
        {children}
      </div>
      <AppFooter />
    </div>
  )
}
