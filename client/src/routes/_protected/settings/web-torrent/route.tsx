import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getSettings } from '@/shared/queries/settings'
import { getTorrents } from '@/shared/queries/torrents'

export const SETTINGS_WEB_TORRENT_NAME = 'WebTorrent'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/web-torrent')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getTorrents),
      context.queryClient.ensureQueryData(getSettings),
    ])
  },
  loader: () => {
    return { breadcrumb: SETTINGS_WEB_TORRENT_NAME }
  },
})
