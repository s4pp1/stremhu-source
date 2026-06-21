import { useQuery } from '@tanstack/react-query'
import {
  CircleCheckBigIcon,
  DownloadIcon,
  PenIcon,
  TimerIcon,
  TrashIcon,
} from 'lucide-react'
import type { JSX, MouseEventHandler } from 'react'
import { useMemo } from 'react'
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
import type { IndexerResponse } from '@/shared/lib/source/source-client'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { useIndexerDelete } from '@/shared/queries/indexers'
import { getSystemSettings } from '@/shared/queries/system'

type IndexerItemProps = {
  indexer: IndexerResponse
}

export function IndexerItem(props: IndexerItemProps) {
  const { data: systemSettings } = useQuery(getSystemSettings)
  assertExists(systemSettings)

  const { indexer } = props

  const dialogs = useDialogs()
  const confirmDialog = useConfirmDialog()

  const { mutateAsync: deleteIndexer } = useIndexerDelete()

  const handleEditIndexer: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()

    dialogs.openDialog({
      type: 'EDIT_INDEXER',
      options: {
        indexer,
      },
    })
  }

  const handleDeleteIndexer: MouseEventHandler<HTMLButtonElement> = async (
    e,
  ) => {
    e.preventDefault()
    e.stopPropagation()

    await confirmDialog.confirm({
      title: `Biztosan törlöd a(z) ${indexer.indexerDefinition.name}-t?`,
      description: `A(z) ${indexer.indexerDefinition.name} törlésével minden aktív torrent törlésre kerül, ami ezen a torrent oldalon fut.`,
      onConfirm: async () => {
        try {
          await deleteIndexer(indexer.indexerId)
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

  const tags = useMemo(() => {
    const items: { label: string; icon: JSX.Element }[] = []

    let hitAndRun = systemSettings.hitAndRun

    if (indexer.hitAndRun !== null) {
      hitAndRun = indexer.hitAndRun
    }

    if (hitAndRun) {
      items.push({ label: `Hit'n'Run`, icon: <CircleCheckBigIcon /> })
    }

    let keepSeedSeconds = systemSettings.keepSeedSeconds

    if (indexer.keepSeedSeconds !== null) {
      keepSeedSeconds = indexer.keepSeedSeconds
    }

    if (keepSeedSeconds) {
      const days = keepSeedSeconds / (24 * 60 * 60)
      items.push({ label: `${days} nap után`, icon: <TimerIcon /> })
    }

    if (indexer.downloadFullTorrent) {
      items.push({ label: `Teljes letöltés`, icon: <DownloadIcon /> })
    }

    return items
  }, [systemSettings, indexer])

  return (
    <Item variant="muted">
      <ItemMedia variant="default">
        <CircleCheckBigIcon className="text-green-700" />
      </ItemMedia>
      <ItemContent>
        <ItemTitle>{indexer.indexerDefinition.name}</ItemTitle>
        <ItemDescription>
          Bejelentkezve <span className="font-bold">{indexer.username}</span>{' '}
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
          onClick={handleEditIndexer}
        >
          <PenIcon />
        </Button>
        <Button
          size="icon-sm"
          variant="destructive"
          className="rounded-full"
          onClick={handleDeleteIndexer}
        >
          <TrashIcon />
        </Button>
      </ItemActions>
    </Item>
  )
}
