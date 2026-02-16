import { Link, Outlet, createFileRoute } from '@tanstack/react-router'

import { Button } from '@/shared/components/ui/button'

import { RouteBreadcrumb } from '../dashboard/-components/route-breadcrumb'
import { SETTINGS_ACCOUNT_NAME } from './account/route'
import { SETTINGS_PREFERENCES_NAME } from './preferences/route'

export const SETTINGS_NAME = 'Beállítások'

export const Route = createFileRoute('/_protected/settings')({
  component: SettingsLayout,
  loader: () => {
    return { breadcrumb: SETTINGS_NAME }
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
              to="/settings/account"
              activeProps={{ className: 'bg-background' }}
            >
              {SETTINGS_ACCOUNT_NAME}
            </Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/settings/preferences"
              activeProps={{ className: 'bg-background' }}
            >
              {SETTINGS_PREFERENCES_NAME}
            </Link>
          </Button>
        </div>
      </div>
      <Outlet />
    </div>
  )
}
