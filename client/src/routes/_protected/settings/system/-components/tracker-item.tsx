import { CircleCheckBigIcon, MoveVerticalIcon, TrashIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/shared/components/ui/item'
import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import type { TrackerDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useDeleteTracker } from '@/shared/queries/trackers'

type Tracker = {
  tracker: TrackerDto
}

export function TrackerItem(props: Tracker) {
  const { tracker } = props

  const confirmDialog = useConfirmDialog()

  const { getTrackerLabel } = useMetadataLabel()

  const { mutateAsync: deleteTracker } = useDeleteTracker()

  const handleDeleteTracker: MouseEventHandler<HTMLButtonElement> = async (
    e,
  ) => {
    e.preventDefault()
    e.stopPropagation()

    await confirmDialog.confirm({
      title: `Biztosan törlöd a(z) ${getTrackerLabel(tracker.tracker)}-t?`,
      description: `A(z) ${getTrackerLabel(tracker.tracker)} törlésével minden aktív torrent törlésre kerül, ami ezen a trackeren fut.`,
      onConfirm: async () => {
        try {
          await deleteTracker(tracker.tracker)
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

  return (
    <Item variant="muted">
      <ItemMedia variant="default">
        <CircleCheckBigIcon className="text-green-700" />
      </ItemMedia>
      <ItemContent>
        <ItemTitle>{getTrackerLabel(tracker.tracker)}</ItemTitle>
        <ItemDescription>
          Bejelentkezve <span className="font-bold">{tracker.username}</span>{' '}
          felhasználóval.
        </ItemDescription>
      </ItemContent>
      <ItemActions>
        <Button size="icon-sm" className="rounded-full">
          <MoveVerticalIcon />
        </Button>
        <Button
          size="icon-sm"
          variant="destructive"
          className="rounded-full"
          onClick={handleDeleteTracker}
        >
          <TrashIcon />
        </Button>
      </ItemActions>
    </Item>
  )
}
