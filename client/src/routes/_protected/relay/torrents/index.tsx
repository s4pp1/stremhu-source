import { useQueries } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { assertExists } from '@/shared/lib/utils'
import { getRelaySettings } from '@/shared/queries/relay'
import { getTorrents } from '@/shared/queries/torrents'

import { Torrents } from './-features/torrents'
import { RELAY_TORRENTS_NAME } from './route'

export const Route = createFileRoute('/_protected/relay/torrents/')({
  component: RouteComponent,
})

function RouteComponent() {
  const [{ data: relay }, { data: torrents }] = useQueries({
    queries: [getRelaySettings, getTorrents],
  })
  assertExists(relay)
  assertExists(torrents)

  return (
    <div className="grid gap-8">
      <Card>
        <CardHeader>
          <CardTitle>
            {RELAY_TORRENTS_NAME}{' '}
            <span className="text-sm text-muted-foreground">
              ({torrents.length})
            </span>
          </CardTitle>
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
