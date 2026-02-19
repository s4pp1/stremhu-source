import { Link } from '@tanstack/react-router'
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

export function UserNavigation() {
  const { isAdmin } = useIsAdmin()

  return (
    <div className="flex gap-2 items-center">
      <Button asChild variant="ghost" size="sm">
        <Link
          to="/"
          activeOptions={{ exact: true }}
          activeProps={{ className: 'bg-background' }}
        >
          Kezdőoldal
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
          <Button variant="outline" size="icon-sm" className="rounded-full">
            <UserIcon />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-40">
          <DropdownMenuGroup>
            <DropdownMenuItem asChild>
              <Link to="/settings">
                <SettingsIcon />
                Beállítások
              </Link>
            </DropdownMenuItem>
            {isAdmin && (
              <DropdownMenuItem asChild>
                <Link to="/dashboard">
                  <LayoutDashboardIcon />
                  Irányítópult
                </Link>
              </DropdownMenuItem>
            )}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem asChild variant="destructive">
              <Link to="/logout">
                <LogOutIcon />
                Kijelentkezés
              </Link>
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
