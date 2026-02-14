import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getRelaySettings } from '@/shared/queries/relay'
import { getTorrents } from '@/shared/queries/torrents'
import { getTrackers } from '@/shared/queries/trackers'

export const RELAY_SETTINGS_NAME = 'Beállítások'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/relay/settings')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getTorrents),
      context.queryClient.ensureQueryData(getRelaySettings),
      context.queryClient.ensureQueryData(getTrackers),
    ])
  },
  loader: () => {
    return { breadcrumb: RELAY_SETTINGS_NAME }
  },
})
