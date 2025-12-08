import {
  Outlet,
  createRootRouteWithContext,
  redirect,
} from '@tanstack/react-router'
import { Toaster } from 'sonner'

import type { RouterContext } from '@/main'
import { getMetadata } from '@/shared/queries/metadata'
import { getSettingsStatus } from '@/shared/queries/settings-setup'

import { Dialogs } from './-features/dialogs/dialogs '
import { AppLayout } from './-features/layout/app-layout'

export const Route = createRootRouteWithContext<RouterContext>()({
  beforeLoad: async ({ context, location }) => {
    const { queryClient } = context
    await queryClient.ensureQueryData(getMetadata)

    const { hasAdminUser } =
      await queryClient.ensureQueryData(getSettingsStatus)

    const onSetup = location.pathname.startsWith('/setup/user')

    if (!hasAdminUser && !onSetup) {
      throw redirect({ to: '/setup/user' })
    }

    if (hasAdminUser && onSetup) {
      throw redirect({ to: '/' })
    }
  },
  component: () => (
    <AppLayout>
      <Outlet />
      <Toaster position="top-center" />
      <Dialogs />
    </AppLayout>
  ),
})
