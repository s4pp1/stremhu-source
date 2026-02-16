import { useQuery } from '@tanstack/react-query'
import { Link, Outlet, createFileRoute } from '@tanstack/react-router'

import { Button } from '@/shared/components/ui/button'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'

import { RouteBreadcrumb } from './-components/route-breadcrumb'
import { SETTINGS_SYSTEM_NAME } from './system/route'
import { SETTINGS_USERS_NAME } from './users/route'

export const Route = createFileRoute('/_protected/dashboard')({
  component: SettingsLayout,
  loader: () => ({
    breadcrumb: 'Irányítópult',
  }),
})

function SettingsLayout() {
  const { data: me } = useQuery(getMe)
  assertExists(me)

  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <RouteBreadcrumb />
        <div className="flex gap-2 items-center bg-card border shadow-sm rounded-md p-1">
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/dashboard/system"
              activeProps={{ className: 'bg-background' }}
            >
              {SETTINGS_SYSTEM_NAME}
            </Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/dashboard/users"
              activeProps={{ className: 'bg-background' }}
            >
              {SETTINGS_USERS_NAME}
            </Link>
          </Button>
        </div>
      </div>
      <Outlet />
    </div>
  )
}
