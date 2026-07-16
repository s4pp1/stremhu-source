import {
  Outlet,
  createRootRouteWithContext,
  redirect,
} from '@tanstack/react-router'
import { Toaster } from 'sonner'

import type { RouterContext } from '@/main'
import { getSystemStatus } from '@/shared/queries/system'

import { Dialogs } from './-features/dialogs/dialogs'
import { AppLayout } from './-features/layout/app-layout'

export const Route = createRootRouteWithContext<RouterContext>()({
  beforeLoad: async ({ context, location }) => {
    const { queryClient } = context

    const { configured } = await queryClient.ensureQueryData(getSystemStatus)

    const onSetup = location.pathname.startsWith('/setup/user')

    if (!configured && !onSetup) {
      throw redirect({ to: '/setup/user' })
    }

    if (configured && onSetup) {
      throw redirect({ to: '/' })
    }
  },
  loader: () => {
    return { breadcrumb: 'Home' }
  },
  component: () => (
    <AppLayout>
      <Outlet />
      <Toaster position="top-center" />
      <Dialogs />
    </AppLayout>
  ),
})
