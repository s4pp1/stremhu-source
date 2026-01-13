import { createFileRoute } from '@tanstack/react-router'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'

import { Connection } from './-features/connection'
import { Speed } from './-features/speed'
import { Torrents } from './-features/torrents'
import { UsedPort } from './-features/used-port'

export const Route = createFileRoute('/_protected/settings/torrent-client/')({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <div className="columns-1 md:columns-2 gap-4">
          <div className="break-inside-avoid mb-4">
            <UsedPort />
          </div>
          <div className="break-inside-avoid mb-4">
            <Speed />
          </div>
          <div className="break-inside-avoid mb-4">
            <Connection />
          </div>
        </div>
      </div>
      <Separator />
      <Card>
        <CardHeader>
          <CardTitle>Aktív torrentek</CardTitle>
          <CardDescription>
            Kövesd nyomon a torrentek statisztikáit és tűzd ki, ha nem
            szeretnéd, hogy autómatikusan törlődjenek.
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent>
          <Torrents />
        </CardContent>
      </Card>
    </div>
  )
}
