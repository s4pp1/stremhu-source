import {
  ArrowBigUpIcon,
  HardDriveDownloadIcon,
  HardDriveIcon,
  HardDriveUploadIcon,
  XIcon,
} from 'lucide-react'
import type { JSX } from 'react'
import { toast } from 'sonner'

import type { TorrentDto } from '@/client/app-client'
import { parseApiError } from '@/common/utils'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useReferenceDataOptionLabel } from '@/hooks/use-reference-data-option-label'
import { useDeleteTorrent } from '@/queries/torrents'
import { useConfirmDialog } from '@/store/confirm-dialog-store'

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

  const { getTrackerLabel } = useReferenceDataOptionLabel()

  const confirmDialog = useConfirmDialog()
  const { mutateAsync: deleteTorrent } = useDeleteTorrent()

  async function handleDelete() {
    await confirmDialog({
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
    <Card key={torrent.infoHash} className="gap-0">
      <CardHeader>
        <CardTitle className="leading-5 line-clamp-2 break-all">
          [{getTrackerLabel(torrent.tracker)}] {torrent.name}
        </CardTitle>
        <CardAction>
          <Button
            size="icon-sm"
            variant="destructive"
            className="rounded-full"
            onClick={handleDelete}
          >
            <XIcon />
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-2">
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
      </CardContent>
    </Card>
  )
}
