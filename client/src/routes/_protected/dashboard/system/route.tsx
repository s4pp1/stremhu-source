import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getIndexers } from '@/shared/queries/indexers'
import { getSystemSettings } from '@/shared/queries/system'
import { getUsers } from '@/shared/queries/users'

export const DASHBOARD_SYSTEM_NAME = 'System'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/dashboard/system')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getSystemSettings),
      context.queryClient.ensureQueryData(getIndexers),
      context.queryClient.ensureQueryData(getUsers),
    ])
  },
  loader: () => {
    return { breadcrumb: DASHBOARD_SYSTEM_NAME }
  },
})
