import { filesize } from 'filesize'
import {
  ArrowBigUpIcon,
  HardDriveDownloadIcon,
  HardDriveIcon,
  HardDriveUploadIcon,
  PinIcon,
  PinOffIcon,
  TrashIcon,
} from 'lucide-react'
import type { JSX, MouseEventHandler } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Toggle } from '@/shared/components/ui/toggle'
import { useMetadata } from '@/shared/hooks/use-metadata'
import type { TorrentDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useDeleteTorrent, useUpdateTorrent } from '@/shared/queries/torrents'

interface TorrentProps {
  torrent: TorrentDto
}

interface TorrentDetailProps {
  icon: JSX.Element
  value: string
}

function TorrentDetail(props: TorrentDetailProps) {
  const { icon, value } = props

  return (
    <div className="flex gap-2 items-center text-muted-foreground text-sm font-normal [&_svg:not([class*='size-'])]:size-4">
      {icon}
      <span className="font-medium">{value}</span>
    </div>
  )
}

export function Torrent(props: TorrentProps) {
  const { torrent } = props

  const { getTrackerLabel } = useMetadata()

  const confirmDialog = useConfirmDialog()

  const { mutateAsync: updateTorrent } = useUpdateTorrent(torrent.infoHash)
  const { mutateAsync: deleteTorrent } = useDeleteTorrent()

  const handleDelete: MouseEventHandler<HTMLButtonElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()

    await confirmDialog.confirm({
      title: `Biztosan törlöd?`,
      description: `A(z) ${torrent.name} törlésével az adatok is törlésre kerülnek.`,
      confirmText: 'Törlés',
      onConfirm: async () => {
        try {
          await deleteTorrent(torrent.infoHash)
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

  const handleUpdate: MouseEventHandler<HTMLButtonElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()

    await updateTorrent({ isPersisted: !torrent.isPersisted })
  }

  return (
    <div className="grid gap-2 border border-transparent rounded-md bg-muted/50 p-4">
      <Item className="p-0">
        <ItemContent>
          <ItemTitle className="line-clamp-2 break-all">
            [{getTrackerLabel(torrent.tracker)}] {torrent.name}
          </ItemTitle>
        </ItemContent>
        <ItemActions>
          <Toggle
            variant="outline"
            size="sm"
            className="rounded-full data-[state=on]:bg-blue-600"
            pressed={torrent.isPersisted}
            onClick={handleUpdate}
          >
            {torrent.isPersisted ? <PinIcon /> : <PinOffIcon />}
          </Toggle>
          <Button
            variant="destructive"
            size="icon-sm"
            className="rounded-full"
            onClick={handleDelete}
          >
            <TrashIcon />
          </Button>
        </ItemActions>
      </Item>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <TorrentDetail
          icon={<HardDriveIcon />}
          value={filesize(torrent.total)}
        />
        <TorrentDetail
          icon={<HardDriveDownloadIcon />}
          value={filesize(torrent.downloaded)}
        />
        <TorrentDetail
          icon={<HardDriveUploadIcon className="size-4" />}
          value={filesize(torrent.uploaded)}
        />
        <TorrentDetail
          icon={<ArrowBigUpIcon className="text-destructive" />}
          value={filesize(torrent.uploadSpeed)}
        />
      </div>
    </div>
  )
}
