import { useQuery } from '@tanstack/react-query'
import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'

import { getMe } from '@/queries/me'

export const Route = createFileRoute('/_protected')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient

    const me = await queryClient.ensureQueryData(getMe)

    if (me === null) {
      throw redirect({ to: '/login' })
    }
  },
  component: ProtectedLayout,
})

function ProtectedLayout() {
  const { data: me } = useQuery(getMe)
  if (!me) throw new Error(`A 'me' nincs a cache-ben.`)

  return <Outlet />
}
