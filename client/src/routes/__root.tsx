import {
  Outlet,
  createRootRouteWithContext,
  redirect,
} from '@tanstack/react-router'
import { Toaster } from 'sonner'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { DialogsRoot } from '@/components/dialogs-root'
import type { RouterContext } from '@/main'
import { getMetadata } from '@/queries/metadata'
import { getSettingsStatus } from '@/queries/settings-setup'

import { AppLayout } from './-components/layouts/app-layout'

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
      <ConfirmDialog />
      <DialogsRoot />
      <Toaster position="top-center" />
    </AppLayout>
  ),
})
