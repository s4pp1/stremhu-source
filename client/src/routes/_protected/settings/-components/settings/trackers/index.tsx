import { useQuery } from '@tanstack/react-query'
import { CircleCheckBigIcon, LogInIcon, TrashIcon } from 'lucide-react'
import { toast } from 'sonner'

import type { TrackerEnum } from '@/client/app-client'
import { parseApiError } from '@/common/utils'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item'
import { getReferenceData } from '@/queries/reference-data'
import { getTrackers, useDeleteTracker } from '@/queries/trackers'
import { useConfirmDialog } from '@/store/confirm-dialog-store'
import { DialogEnum, useDialogs } from '@/store/dialogs-store'

export function Trackers() {
  const { data: trackers } = useQuery(getTrackers)
  const { data: referenceData } = useQuery(getReferenceData)

  if (!referenceData) throw new Error(`Nincs "reference-data" a cache-ben`)
  if (!trackers) throw new Error(`Nincs "trackers" a cache-ben`)

  const { handleOpen } = useDialogs()

  const confirmDialog = useConfirmDialog()
  const { mutateAsync: deleteTracker } = useDeleteTracker()

  const { labelMap, option } = referenceData

  const renderTrackerLogin = option.trackers.length !== trackers.length

  const handleDeleteTracker = async (tracker: TrackerEnum) => {
    await confirmDialog({
      title: `Biztosan törlöd a ${labelMap.tracker[tracker]}-t?`,
      description: `A törlést követően az ${labelMap.tracker[tracker]} torrentek már nem fognak megjelenni a Stremio-ban.`,
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
          egyik támogatott tracker-be. [
          <span className="font-bold">
            {option.trackers.map((tracker) => tracker.label).join(', ')}
          </span>
          ]
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {trackers.map(({ tracker, username }) => (
          <Item key={tracker} variant="default" className="p-0">
            <ItemMedia variant="default">
              <CircleCheckBigIcon className="text-green-700" />
            </ItemMedia>
            <ItemContent>
              <ItemTitle>{labelMap.tracker[tracker]}</ItemTitle>
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
                  handleOpen({
                    dialog: DialogEnum.ADD_TRACKER,
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
