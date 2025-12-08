import { useQuery } from '@tanstack/react-query'
import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'

import { UserRoleEnum } from '@/shared/lib/source-client'
import { getMe } from '@/shared/queries/me'
import { getSettingsStatus } from '@/shared/queries/settings-setup'

export const Route = createFileRoute('/_protected')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient

    const me = await queryClient.ensureQueryData(getMe)
    const { hasAddress } = await queryClient.ensureQueryData(getSettingsStatus)

    if (me === null) {
      throw redirect({ to: '/login' })
    }

    const onSetup = location.pathname.startsWith('/setup/address')

    if (!hasAddress && !onSetup) {
      if (me.userRole !== UserRoleEnum.ADMIN) {
        throw new Error(
          `Az addon konfigurációja még nem készült el. Kérd meg az adminisztrátort a beállítás befejezésére.`,
        )
      }

      throw redirect({ to: '/setup/address' })
    }
  },
  component: ProtectedLayout,
})

function ProtectedLayout() {
  const { data: me } = useQuery(getMe)
  if (!me) throw new Error(`A 'me' nincs a cache-ben.`)

  return <Outlet />
}
