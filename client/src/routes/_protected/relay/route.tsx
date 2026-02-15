import { Link, Outlet, createFileRoute } from '@tanstack/react-router'

import { Button } from '@/shared/components/ui/button'

import { RouteBreadcrumb } from '../dashboard/-components/route-breadcrumb'
import { RELAY_TORRENTS_NAME } from './torrents/route'

export const SETTINGS_RELAY_NAME = 'Relay'

export const Route = createFileRoute('/_protected/relay')({
  component: SettingsLayout,
  loader: () => {
    return { breadcrumb: SETTINGS_RELAY_NAME }
  },
})

function SettingsLayout() {
  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <RouteBreadcrumb />
        <div className="flex gap-2 items-center bg-card border shadow-sm rounded-md p-1">
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/relay/torrents"
              activeProps={{ className: 'bg-background' }}
            >
              {RELAY_TORRENTS_NAME}
            </Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/relay/settings"
              activeProps={{ className: 'bg-background' }}
            >
              Beállítások
            </Link>
          </Button>
        </div>
      </div>
      <Outlet />
    </div>
  )
}
