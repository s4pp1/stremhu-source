import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Trans } from '@lingui/react/macro'
import {
  LayoutDashboardIcon,
  LogOutIcon,
  SettingsIcon,
  UserIcon,
} from 'lucide-react'

import { SETTINGS_RELAY_NAME } from '@/routes/_protected/relay/route'
import { Button } from '@/shared/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'
import { useIsAdmin } from '@/shared/hooks/use-is-admin'
import { getMe } from '@/shared/queries/me'

export function UserNavigation() {
  const { data: me } = useQuery(getMe())

  const { isAdmin } = useIsAdmin()

  if (!me) return null

  return (
    <div className="flex gap-2 items-center">
      <Button asChild variant="ghost" size="sm">
        <Link
          to="/"
          activeOptions={{ exact: true }}
          activeProps={{ className: 'bg-background' }}
        >
          <Trans>Home</Trans>
        </Link>
      </Button>
      {isAdmin && (
        <Button asChild variant="ghost" size="sm">
          <Link to="/relay" activeProps={{ className: 'bg-background' }}>
            {SETTINGS_RELAY_NAME}
          </Link>
        </Button>
      )}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="rounded-full">
            <UserIcon />
            {me.username}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-40" align="end">
          <DropdownMenuGroup>
            <DropdownMenuItem asChild>
              <Link to="/settings">
                <SettingsIcon />
                <Trans>Settings</Trans>
              </Link>
            </DropdownMenuItem>
            {isAdmin && (
              <DropdownMenuItem asChild>
                <Link to="/dashboard">
                  <LayoutDashboardIcon />
                  <Trans>Dashboard</Trans>
                </Link>
              </DropdownMenuItem>
            )}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem asChild variant="destructive">
              <Link to="/logout">
                <LogOutIcon />
                <Trans>Logout</Trans>
              </Link>
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
