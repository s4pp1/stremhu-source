import type { PropsWithChildren } from 'react'

export function AppLayout(props: PropsWithChildren) {
  const { children } = props

  return (
    <div className="container mx-auto max-w-3xl">
      <div className="px-4">{children}</div>
    </div>
  )
}
