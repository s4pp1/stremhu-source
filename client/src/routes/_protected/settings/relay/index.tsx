import { useQueries } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { SettingsIcon } from 'lucide-react'

import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
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
import { SETTINGS_RELAY_NAME } from './route'

export const Route = createFileRoute('/_protected/settings/relay/')({
  component: RouteComponent,
})

function RouteComponent() {
  const dialogs = useDialogs()

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
            {SETTINGS_RELAY_NAME} <span>({torrents.length})</span>
          </CardTitle>
          <CardDescription>
            Kövesd nyomon a torrentek statisztikáit és tűzd ki, ha nem
            szeretnéd, hogy autómatikusan törlődjenek.
          </CardDescription>
          <CardAction>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() =>
                dialogs.openDialog({ type: 'EDIT_RELAY', options: { relay } })
              }
            >
              <SettingsIcon />
            </Button>
          </CardAction>
        </CardHeader>
        <Separator />
        <CardContent>
          <Torrents />
        </CardContent>
      </Card>
    </div>
  )
}
