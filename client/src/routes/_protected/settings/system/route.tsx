import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getSettings } from '@/shared/queries/settings'
import { getTrackers } from '@/shared/queries/trackers'
import { getUsers } from '@/shared/queries/users'

export const SETTINGS_SYSTEM_NAME = 'Rendszer'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/system')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getSettings),
      context.queryClient.ensureQueryData(getTrackers),
      context.queryClient.ensureQueryData(getUsers),
    ])
  },
  loader: () => {
    return { breadcrumb: SETTINGS_SYSTEM_NAME }
  },
})
