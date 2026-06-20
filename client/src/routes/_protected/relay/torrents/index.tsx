import { useSuspenseQueries } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { getTorrents } from '@/shared/queries/torrents'

import { Torrents } from './-features/torrents'
import { RELAY_TORRENTS_NAME } from './route'

export const Route = createFileRoute('/_protected/relay/torrents/')({
  component: RouteComponent,
})

function RouteComponent() {
  const [{ data: torrents }] = useSuspenseQueries({
    queries: [getTorrents],
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {RELAY_TORRENTS_NAME}{' '}
          <span className="text-sm text-muted-foreground">
            ({torrents.length})
          </span>
        </CardTitle>
        <CardDescription>
          Torrentek aktuális statisztikái és a hozzájuk kapcsolódó műveletek.
        </CardDescription>
      </CardHeader>
      <Separator />
      <CardContent>
        <Torrents />
      </CardContent>
    </Card>
  )
}
