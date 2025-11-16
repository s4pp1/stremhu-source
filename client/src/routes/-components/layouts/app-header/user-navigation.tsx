import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { LogOutIcon } from 'lucide-react'

import { UserRoleEnum } from '@/client/app-client'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { getMe } from '@/queries/me'

export function UserNavigation() {
  const { data: me } = useQuery(getMe)
  if (!me) return null

  return (
    <div className="flex gap-2 items-center">
      <Button asChild variant="ghost" size="sm">
        <Link
          to="/"
          activeOptions={{ exact: true }}
          activeProps={{ className: 'bg-background' }}
        >
          Fiókom
        </Link>
      </Button>
      {me.userRole === UserRoleEnum.ADMIN && (
        <Button asChild variant="ghost" size="sm">
          <Link
            to="/settings"
            activeOptions={{ exact: true }}
            activeProps={{ className: 'bg-background' }}
          >
            Beállítások
          </Link>
        </Button>
      )}
      <Tooltip delayDuration={500}>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon" className="text-destructive">
            <Link to="/logout">
              <LogOutIcon />
            </Link>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>Kijelentkezés</p>
        </TooltipContent>
      </Tooltip>
    </div>
  )
}
