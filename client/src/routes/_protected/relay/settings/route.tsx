import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getRelaySettings } from '@/shared/queries/relay'

export const RELAY_SETTINGS_NAME = 'Settings'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/relay/settings')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([context.queryClient.ensureQueryData(getRelaySettings)])
  },
  loader: () => {
    return { breadcrumb: RELAY_SETTINGS_NAME }
  },
})
