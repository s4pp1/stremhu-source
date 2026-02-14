import { useQuery } from '@tanstack/react-query'
import {
  CircleCheckBigIcon,
  DownloadIcon,
  PenIcon,
  TimerIcon,
  TrashIcon,
} from 'lucide-react'
import { useMemo } from 'react'
import type { JSX, MouseEventHandler } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
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
import { useMetadata } from '@/shared/hooks/use-metadata'
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

  const dialogs = useDialogs()
  const confirmDialog = useConfirmDialog()

  const { getTrackerLabel } = useMetadata()

  const { mutateAsync: deleteTracker } = useDeleteTracker()

  const handleEditTracker: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()

    dialogs.openDialog({
      type: 'EDIT_TRACKER',
      options: {
        tracker,
      },
    })
  }

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

  const tags = useMemo(() => {
    const items: Array<{ label: string; icon: JSX.Element }> = []

    let hitAndRun = setting.hitAndRun

    if (tracker.hitAndRun !== null) {
      hitAndRun = tracker.hitAndRun
    }

    if (hitAndRun) {
      items.push({ label: `Hit'n'Run`, icon: <CircleCheckBigIcon /> })
    }

    let keepSeedSeconds = setting.keepSeedSeconds

    if (tracker.keepSeedSeconds !== null) {
      keepSeedSeconds = tracker.keepSeedSeconds
    }

    if (keepSeedSeconds) {
      const days = keepSeedSeconds / (24 * 60 * 60)
      items.push({ label: `${days} nap seedben`, icon: <TimerIcon /> })
    }

    if (tracker.downloadFullTorrent) {
      items.push({ label: `Teljes letöltés`, icon: <DownloadIcon /> })
    }

    return items
  }, [setting, tracker])

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
        {tags.length !== 0 && (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <Badge key={tag.label} variant="secondary">
                {tag.icon}
                {tag.label}
              </Badge>
            ))}
          </div>
        )}
      </ItemContent>
      <ItemActions>
        <Button
          size="icon-sm"
          className="rounded-full"
          onClick={handleEditTracker}
        >
          <PenIcon />
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
