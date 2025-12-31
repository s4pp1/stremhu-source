import { useQuery } from '@tanstack/react-query'
import { Link, Outlet, createFileRoute } from '@tanstack/react-router'

import { Button } from '@/shared/components/ui/button'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'

import { SettingsBreadcrumb } from './-components/settings-breadcrumb'
import { SETTINGS_SYSTEM_NAME } from './system/route'
import { SETTINGS_TORRENT_CLIENT_NAME } from './torrent-client/route'
import { SETTINGS_USERS_NAME } from './users/route'

export const Route = createFileRoute('/_protected/settings')({
  component: SettingsLayout,
  loader: () => ({
    breadcrumb: 'Beállítások',
  }),
})

function SettingsLayout() {
  const { data: me } = useQuery(getMe)
  assertExists(me)

  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <SettingsBreadcrumb />
        <div className="flex gap-2 items-center bg-card border shadow-sm rounded-md p-1">
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/settings/system"
              activeProps={{ className: 'bg-background' }}
            >
              {SETTINGS_SYSTEM_NAME}
            </Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/settings/users"
              activeProps={{ className: 'bg-background' }}
            >
              {SETTINGS_USERS_NAME}
            </Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/settings/torrent-client"
              activeProps={{ className: 'bg-background' }}
            >
              {SETTINGS_TORRENT_CLIENT_NAME}
            </Link>
          </Button>
        </div>
      </div>

      <Outlet />
    </div>
  )
}
