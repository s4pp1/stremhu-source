import { createFileRoute } from '@tanstack/react-router'

import {
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'

import { LoginAndSecurity } from './-features/login-and-security'
import { MeConfig } from './-features/me-config'
import { OtherTorrentsPreferences } from './-features/other-torrents-preferences'
import { TorrentsPreferences } from './-features/torrents-preferences'

export const Route = createFileRoute('/_protected/')({
  component: ProfileRoute,
})

function ProfileRoute() {
  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <CardHeader className="px-0">
          <CardTitle>Stream preferenciák</CardTitle>
          <CardDescription>
            Konfiguráld, hogy a Stremio-ban megjelenő torrenteknél mik a
            preferenciáid és ennek megfelelően fognak megjelenni.
          </CardDescription>
        </CardHeader>
        <TorrentsPreferences />
      </div>
      <Separator />
      <div className="grid gap-4">
        <CardHeader className="px-0">
          <CardTitle>További stream preferenciák</CardTitle>
          <CardDescription>
            Konfiguráld, hogy a Stremio-ban megjelenő torrenteknél mik a
            preferenciáid és ennek megfelelően fognak megjelenni.
          </CardDescription>
        </CardHeader>
        <OtherTorrentsPreferences />
      </div>
      <Separator />
      <div className="grid gap-4">
        <CardHeader className="px-0">
          <CardTitle>Fiókbeállítások és Stremio-integráció</CardTitle>
          <CardDescription>
            Itt módosíthatod a belépési adataidat és biztonsági beállításaidat,
            valamint összekapcsolhatod az addont a Stremio-fiókoddal.
          </CardDescription>
        </CardHeader>
        <div className="columns-1 md:columns-2 gap-4">
          <div className="break-inside-avoid mb-4">
            <LoginAndSecurity />
          </div>
          <div className="break-inside-avoid mb-4">
            <MeConfig />
          </div>
        </div>
      </div>
    </div>
  )
}
