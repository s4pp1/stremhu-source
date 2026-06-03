import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getTrackers } from '@/shared/queries/indexers'
import { getSettings } from '@/shared/queries/settings'
import { getUsers } from '@/shared/queries/users'

export const DASHBOARD_SYSTEM_NAME = 'Rendszer'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/dashboard/system')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getSettings),
      context.queryClient.ensureQueryData(getTrackers),
      context.queryClient.ensureQueryData(getUsers),
    ])
  },
  loader: () => {
    return { breadcrumb: DASHBOARD_SYSTEM_NAME }
  },
})
