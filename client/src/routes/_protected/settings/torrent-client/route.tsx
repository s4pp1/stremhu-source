import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getSettings } from '@/shared/queries/settings'
import { getTorrents } from '@/shared/queries/torrents'

export const SETTINGS_TORRENT_CLIENT_NAME = 'Torrent Kliens'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/torrent-client')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getTorrents),
      context.queryClient.ensureQueryData(getSettings),
    ])
  },
  loader: () => {
    return { breadcrumb: SETTINGS_TORRENT_CLIENT_NAME }
  },
})
