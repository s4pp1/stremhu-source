import { useQueries } from '@tanstack/react-query'
import { LogInIcon } from 'lucide-react'

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
import type { TrackerEnum } from '@/shared/lib/source-client'
import { assertExists } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'
import { getTrackers } from '@/shared/queries/trackers'

import { TrackerItem } from '../-components/tracker-item'
import { HitAndRun } from './hit-and-run'

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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trackerek</CardTitle>
        <CardDescription>
          Az addon használatához meg kell adnom a bejelentkezési adataidat az
          egyik támogatott tracker-be.
        </CardDescription>
        {renderTrackerLogin && (
          <CardAction>
            <Button
              size="icon-sm"
              className="rounded-full bg-green-700 text-white"
              onClick={() =>
                dialogs.openDialog({
                  type: 'ADD_TRACKER',
                  options: { activeTrackers },
                })
              }
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
        <Separator />
        <HitAndRun />
      </CardContent>
    </Card>
  )
}
