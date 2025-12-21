import { useQueries } from '@tanstack/react-query'
import { LogInIcon } from 'lucide-react'
import type { FormEventHandler } from 'react'

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
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/shared/components/ui/empty'
import { Separator } from '@/shared/components/ui/separator'
import type { TrackerEnum } from '@/shared/lib/source-client'
import { assertExists } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'
import { getTrackers } from '@/shared/queries/trackers'

import { TrackerItem } from '../-components/tracker-item'

export function Trackers() {
  const [{ data: trackers }, { data: metadata }] = useQueries({
    queries: [getTrackers, getMetadata],
  })

  assertExists(metadata)
  assertExists(trackers)

  const dialogs = useDialogs()

  const renderTrackerLogin = metadata.trackers.length !== trackers.length

  const activeTrackers: Array<TrackerEnum> = trackers.map(
    (tracker) => tracker.tracker,
  )

  const handleTrackerLogin: FormEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dialogs.openDialog({
      type: 'ADD_TRACKER',
      options: { activeTrackers },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trackerek</CardTitle>
        <CardDescription>
          Kezeld a tracker-eket és módosítsd a konfigurációit.
        </CardDescription>
        {renderTrackerLogin && (
          <CardAction>
            <Button
              size="icon-sm"
              className="rounded-full bg-green-700 text-white"
              onClick={handleTrackerLogin}
            >
              <LogInIcon />
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <Separator />
      <CardContent className="grid gap-4">
        {trackers.map((tracker) => (
          <TrackerItem key={tracker.tracker} tracker={tracker} />
        ))}
        {trackers.length === 0 && (
          <Empty className="p-2 md:p-2">
            <EmptyHeader>
              <EmptyTitle>Jelentkezz be!</EmptyTitle>
              <EmptyDescription>
                Az addon használatához, be kell jelentkezned legalább egy
                tracker-be!
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="bg-green-700 text-white"
                  onClick={handleTrackerLogin}
                >
                  <LogInIcon />
                  Bejelentkezés
                </Button>
              </div>
            </EmptyContent>
          </Empty>
        )}
      </CardContent>
    </Card>
  )
}
