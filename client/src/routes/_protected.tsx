import { useQuery } from '@tanstack/react-query'
import { Link, Outlet, createFileRoute, redirect } from '@tanstack/react-router'
import { LogOutIcon } from 'lucide-react'

import { UserRoleEnum } from '@/client/app-client'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { getMe } from '@/queries/me'

export const Route = createFileRoute('/_protected')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient

    try {
      await queryClient.ensureQueryData(getMe)
    } catch (error) {
      throw redirect({ to: '/login' })
    }
  },
  component: ProtectedLayout,
})

function ProtectedLayout() {
  const { data: me } = useQuery(getMe)
  if (!me) throw new Error(`A 'me' nincs a cache-ben.`)

  return (
    <div className="pt-18 pb-4">
      <div className="fixed flex justify-center items-center w-full h-14 top-0 left-0 bg-card border-b border-b-background z-50">
        <div className="flex justify-between items-center w-full max-w-3xl px-4">
          <Link to="/" className="flex items-center gap-2 font-medium">
            <img src="/logo.png" alt="StremHU" className="h-8 w-auto" />
            Source
          </Link>
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
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive"
                >
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
        </div>
      </div>
      <Outlet />
    </div>
  )
}
