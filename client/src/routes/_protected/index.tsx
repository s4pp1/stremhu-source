import { Link, createFileRoute } from '@tanstack/react-router'
import {
  ChevronRightIcon,
  LayoutDashboardIcon,
  ListVideoIcon,
  ShieldUserIcon,
  UsersIcon,
} from 'lucide-react'

import { Button } from '@/shared/components/ui/button'
import {
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Separator } from '@/shared/components/ui/separator'
import { useIsAdmin } from '@/shared/hooks/use-is-admin'

import { Integration } from './-features/integration'
import { DASHBOARD_SYSTEM_NAME } from './dashboard/system/route'
import { DASHBOARD_USERS_NAME } from './dashboard/users/route'
import { SETTINGS_ACCOUNT_NAME } from './settings/account/route'
import { SETTINGS_PREFERENCES_NAME } from './settings/preferences/route'

export const Route = createFileRoute('/_protected/')({
  component: ProfileRoute,
})

function ProfileRoute() {
  const { isAdmin } = useIsAdmin()

  return (
    <div className="grid gap-8">
      <Integration />
      <Separator />
      <div className="grid gap-4">
        <CardHeader className="px-0">
          <CardTitle>Beállítások</CardTitle>
          <CardDescription>
            Módosíthatod a fiókadataidat, biztonsági beállításaidat és a
            torrentlista preferenciáit.
          </CardDescription>
        </CardHeader>
        <div className="grid gap-4">
          <Item asChild variant="muted">
            <Link to="/settings/account">
              <ItemMedia variant="icon">
                <ShieldUserIcon />
              </ItemMedia>
              <ItemContent>
                <ItemTitle>
                  {SETTINGS_ACCOUNT_NAME} - Bejelentkezés és biztonság
                </ItemTitle>
                <ItemDescription>
                  Bejelentkezési adatok, jelszó és biztonsági beállítások
                  kezelése.
                </ItemDescription>
              </ItemContent>
              <ItemActions>
                <Button
                  className="rounded-full"
                  size="icon-sm"
                  variant="default"
                >
                  <ChevronRightIcon />
                </Button>
              </ItemActions>
            </Link>
          </Item>
          <Item asChild variant="muted">
            <Link to="/settings/preferences">
              <ItemMedia variant="icon">
                <ListVideoIcon />
              </ItemMedia>
              <ItemContent>
                <ItemTitle>
                  {SETTINGS_PREFERENCES_NAME} - Torrent lista személyreszabása
                </ItemTitle>
                <ItemDescription>
                  Állítsd be, mi kerüljön előre a találatok között, és mit
                  zárjunk ki.
                </ItemDescription>
              </ItemContent>
              <ItemActions>
                <Button
                  className="rounded-full"
                  size="icon-sm"
                  variant="default"
                >
                  <ChevronRightIcon />
                </Button>
              </ItemActions>
            </Link>
          </Item>
        </div>
      </div>
      {isAdmin && (
        <>
          <Separator />
          <div className="grid gap-4">
            <CardHeader className="px-0">
              <CardTitle>Irányítópult</CardTitle>
              <CardDescription>
                Rendszer konfigurálása és felhasználók kezelése.
              </CardDescription>
            </CardHeader>
            <div className="grid gap-4">
              <Item asChild variant="muted">
                <Link to="/dashboard/system">
                  <ItemMedia variant="icon">
                    <LayoutDashboardIcon />
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{DASHBOARD_SYSTEM_NAME}</ItemTitle>
                    <ItemDescription>
                      Tracker bejelentkezések kezelése, StremHU Source
                      konfigurálása.
                    </ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Button
                      className="rounded-full"
                      size="icon-sm"
                      variant="default"
                    >
                      <ChevronRightIcon />
                    </Button>
                  </ItemActions>
                </Link>
              </Item>
              <Item asChild variant="muted">
                <Link to="/dashboard/users">
                  <ItemMedia variant="icon">
                    <UsersIcon />
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{DASHBOARD_USERS_NAME}</ItemTitle>
                    <ItemDescription>
                      Felhasználói fiókok létrehozása, profiladatok kezelése és
                      frissítése.
                    </ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Button
                      className="rounded-full"
                      size="icon-sm"
                      variant="default"
                    >
                      <ChevronRightIcon />
                    </Button>
                  </ItemActions>
                </Link>
              </Item>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
