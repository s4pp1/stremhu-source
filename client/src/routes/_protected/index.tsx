import { Link, createFileRoute } from '@tanstack/react-router'
import { ChevronRightIcon, ListVideoIcon, ShieldUserIcon } from 'lucide-react'

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

import { MeConfig } from './-features/me-config'
import { SETTINGS_ACCOUNT_NAME } from './settings/account/route'
import { SETTINGS_PREFERENCES_NAME } from './settings/preferences/route'

export const Route = createFileRoute('/_protected/')({
  component: ProfileRoute,
})

function ProfileRoute() {
  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <CardHeader className="px-0">
          <CardTitle>Integráció</CardTitle>
          <CardDescription>
            Addon összekapcsolása a Stremio-fiókoddal.
          </CardDescription>
        </CardHeader>
        <div className="columns-1 md:columns-2 gap-4">
          <div className="break-inside-avoid mb-4">
            <MeConfig />
          </div>
        </div>
      </div>
      <Separator />
      <div className="grid gap-4">
        <CardHeader className="px-0">
          <CardTitle>Beállítások</CardTitle>
          <CardDescription>
            Itt módosíthatod a fiókadataidat, biztonsági beállításaidat és a
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
    </div>
  )
}
