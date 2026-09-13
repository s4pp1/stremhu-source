import { useSuspenseQueries } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { HardDriveDownloadIcon, HardDriveIcon } from 'lucide-react'

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { getTorrents, getTorrentsStorage } from '@/shared/queries/torrents'
import { formatFilesize } from '@/shared/utils/file.util'

import { Torrents } from './-features/torrents'
import { RELAY_TORRENTS_NAME } from './route'

export const Route = createFileRoute('/_protected/relay/torrents/')({
  component: RouteComponent,
})

function RouteComponent() {
  const [{ data: torrents }, { data: storage }] = useSuspenseQueries({
    queries: [getTorrents, getTorrentsStorage],
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
        <CardAction className="text-muted-foreground grid gap-1 text-sm">
          <span className="flex items-center gap-2">
            <HardDriveDownloadIcon className="size-4 shrink-0" />
            {formatFilesize(storage.usedBytes)} letöltve
          </span>
          <span className="flex items-center gap-2">
            <HardDriveIcon className="size-4 shrink-0" />
            {formatFilesize(storage.freeBytes)} szabad
          </span>
        </CardAction>
      </CardHeader>
      <Separator />
      <CardContent>
        <Torrents />
      </CardContent>
    </Card>
  )
}
