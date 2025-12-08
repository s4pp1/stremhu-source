import { useQuery } from '@tanstack/react-query'
import { CircleCheckBigIcon, LogInIcon, TrashIcon } from 'lucide-react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
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
import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import type { TrackerEnum } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'
import { getTrackers, useDeleteTracker } from '@/shared/queries/trackers'

export function Trackers() {
  const { data: trackers } = useQuery(getTrackers)
  const { data: metadata } = useQuery(getMetadata)

  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)
  if (!trackers) throw new Error(`Nincs "trackers" a cache-ben`)

  const dialogs = useDialogs()
  const confirmDialog = useConfirmDialog()
  const { getTrackerLabel } = useMetadataLabel()

  const { mutateAsync: deleteTracker } = useDeleteTracker()

  const renderTrackerLogin = metadata.trackers.length !== trackers.length

  const handleDeleteTracker = async (tracker: TrackerEnum) => {
    await confirmDialog.confirm({
      title: `Biztosan törlöd a(z) ${getTrackerLabel(tracker)}-t?`,
      description: `A(z) ${getTrackerLabel(tracker)} törlésével minden aktív torrent törlésre kerül, ami ezen a trackeren fut.`,
      onConfirm: async () => {
        try {
          await deleteTracker(tracker)
          toast.success('Sikeres törlés')
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

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
      </CardHeader>
      <CardContent className="grid gap-4">
        {trackers.map(({ tracker, username }) => (
          <Item key={tracker} variant="default" className="p-0">
            <ItemMedia variant="default">
              <CircleCheckBigIcon className="text-green-700" />
            </ItemMedia>
            <ItemContent>
              <ItemTitle>{getTrackerLabel(tracker)}</ItemTitle>
              <ItemDescription>
                Bejelentkezve <span className="font-bold">{username}</span>{' '}
                felhasználóval.
              </ItemDescription>
            </ItemContent>
            <ItemActions>
              <Button
                size="icon-sm"
                variant="destructive"
                className="rounded-full"
                onClick={() => handleDeleteTracker(tracker)}
              >
                <TrashIcon />
              </Button>
            </ItemActions>
          </Item>
        ))}
        {renderTrackerLogin && (
          <Item variant="default" className="p-0">
            <ItemContent>
              <ItemTitle>Tracker csatlakoztatása</ItemTitle>
              <ItemDescription className="line-clamp-3">
                Indítsd el a bejelentkezést a trackerhez. A hitelesítés után az
                addon használhatja a fiókodat.
              </ItemDescription>
            </ItemContent>
            <ItemActions>
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
            </ItemActions>
          </Item>
        )}
      </CardContent>
    </Card>
  )
}
