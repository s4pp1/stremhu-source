import {
  ArrowBigUpIcon,
  HardDriveDownloadIcon,
  HardDriveIcon,
  HardDriveUploadIcon,
  PinIcon,
  TrashIcon,
} from 'lucide-react'
import type { JSX } from 'react'
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
import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import type { TorrentDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useDeleteTorrent } from '@/shared/queries/torrents'

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

  const { getTrackerLabel } = useMetadataLabel()

  const confirmDialog = useConfirmDialog()
  const { mutateAsync: deleteTorrent } = useDeleteTorrent()

  async function handleDelete() {
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

  return (
    <div className="grid gap-2 border border-transparent rounded-md bg-muted/50 p-4">
      <Item className="p-0">
        <ItemContent>
          <ItemTitle className="line-clamp-2 break-all">
            [{getTrackerLabel(torrent.tracker)}] {torrent.name}
          </ItemTitle>
        </ItemContent>
        <ItemActions>
          <Toggle variant="outline" className="rounded-full">
            <PinIcon />
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
        <TorrentDetail icon={<HardDriveIcon />} value={torrent.total} />
        <TorrentDetail
          icon={<HardDriveDownloadIcon />}
          value={torrent.downloaded}
        />
        <TorrentDetail
          icon={<HardDriveUploadIcon className="size-4" />}
          value={torrent.uploaded}
        />
        <TorrentDetail
          icon={<ArrowBigUpIcon className="text-destructive" />}
          value={torrent.uploadSpeed}
        />
      </div>
    </div>
  )
}
