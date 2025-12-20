import { useQuery } from '@tanstack/react-query'
import {
  CircleCheckBigIcon,
  DownloadIcon,
  MoveVerticalIcon,
  TimerIcon,
  TrashIcon,
} from 'lucide-react'
import { useMemo } from 'react'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Badge } from '@/shared/components/ui/badge'
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
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getSettings } from '@/shared/queries/settings'
import { useDeleteTracker } from '@/shared/queries/trackers'

type Tracker = {
  tracker: TrackerDto
}

export function TrackerItem(props: Tracker) {
  const { data: setting } = useQuery(getSettings)
  assertExists(setting)

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

  const keepSeedDays = useMemo(() => {
    if (setting.keepSeedSeconds) {
      const days = setting.keepSeedSeconds / (24 * 60 * 60)
      return `${days}`
    }

    return null
  }, [setting.keepSeedSeconds])

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
        <div className="flex flex-wrap gap-2">
          {setting.hitAndRun && (
            <Badge variant="secondary">
              <CircleCheckBigIcon />
              Hit'n'Run
            </Badge>
          )}
          {keepSeedDays && (
            <Badge variant="secondary">
              <TimerIcon />
              {keepSeedDays} nap seedben
            </Badge>
          )}
          {tracker.downloadFullTorrent && (
            <Badge variant="secondary">
              <DownloadIcon />
              Teljes letöltés
            </Badge>
          )}
        </div>
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
