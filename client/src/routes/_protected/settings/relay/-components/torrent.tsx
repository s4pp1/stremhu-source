import { useQuery } from '@tanstack/react-query'
import {
  ArrowBigDownIcon,
  ArrowBigUpIcon,
  EllipsisVerticalIcon,
  ExternalLinkIcon,
  FileDownIcon,
  FolderDownIcon,
  HardDriveDownloadIcon,
  HardDriveIcon,
  HardDriveUploadIcon,
  PinIcon,
  PinOffIcon,
  RotateCcwIcon,
  TrashIcon,
} from 'lucide-react'
import type { JSX, MouseEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { formatFilesize } from '@/common/file.util'
import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemTitle,
} from '@/shared/components/ui/item'
import { useMetadata } from '@/shared/hooks/use-metadata'
import type { TorrentDto } from '@/shared/lib/source-client'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { useDeleteTorrent, useUpdateTorrent } from '@/shared/queries/torrents'
import { getTrackers } from '@/shared/queries/trackers'

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

  const { data: trackers } = useQuery(getTrackers)
  assertExists(trackers)

  const { getTrackerLabel, getTrackerUrl } = useMetadata()

  const confirmDialog = useConfirmDialog()

  const { mutateAsync: updateTorrent } = useUpdateTorrent(torrent.infoHash)
  const { mutateAsync: deleteTorrent } = useDeleteTorrent()

  const fullDownload = useMemo(() => {
    const trackerFullDownload =
      trackers.find((tracker) => tracker.tracker === torrent.tracker)
        ?.downloadFullTorrent ?? false

    if (torrent.fullDownload === null) {
      return trackerFullDownload
    }

    return torrent.fullDownload
  }, [torrent, trackers])

  const handleDelete: MouseEventHandler<HTMLDivElement> = async (e) => {
    e.stopPropagation()

    await confirmDialog.confirm({
      title: `Biztosan törlöd?`,
      description: (
        <>
          A(z) <span className="font-bold break-all">{torrent.name}</span>{' '}
          törlésével az adatok is törlésre kerülnek.
        </>
      ),
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

  const handleUpdate: MouseEventHandler<HTMLDivElement> = async (e) => {
    e.stopPropagation()

    await updateTorrent({ isPersisted: !torrent.isPersisted })
  }

  const handleOpenDetails: MouseEventHandler<HTMLDivElement> = (e) => {
    e.stopPropagation()

    const trackerUrl = getTrackerUrl(torrent.tracker)

    const detailsPath = trackerUrl.detailsPath.replace(
      '{torrentId}',
      torrent.torrentId,
    )
    const url = new URL(detailsPath, trackerUrl.url)

    console.log('url.href', url.href)

    window.open(url.href, '_blank', 'noopener,noreferrer')
  }

  const handleFullDownload =
    (value: boolean | null): MouseEventHandler<HTMLDivElement> =>
    async (e) => {
      e.stopPropagation()

      await updateTorrent({ fullDownload: value })
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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon-sm" className="rounded-full">
                <EllipsisVerticalIcon />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-64">
              <DropdownMenuGroup>
                <DropdownMenuItem onClick={handleOpenDetails}>
                  <ExternalLinkIcon />
                  Adatlap megnyitása
                </DropdownMenuItem>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                <DropdownMenuItem onClick={handleUpdate}>
                  {torrent.isPersisted ? (
                    <>
                      <PinOffIcon />
                      Seedben tartás megszüntetése
                    </>
                  ) : (
                    <>
                      <PinIcon />
                      Seedben tartás
                    </>
                  )}
                </DropdownMenuItem>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                {fullDownload ? (
                  <DropdownMenuItem onClick={handleFullDownload(false)}>
                    <FileDownIcon />
                    Teljes letöltés megszüntetése
                  </DropdownMenuItem>
                ) : (
                  <DropdownMenuItem onClick={handleFullDownload(true)}>
                    <FolderDownIcon />
                    Teljes letöltés
                  </DropdownMenuItem>
                )}
                {torrent.fullDownload !== null && (
                  <DropdownMenuItem onClick={handleFullDownload(null)}>
                    <RotateCcwIcon />
                    Letöltés visszaállítása a tracker beállításra
                  </DropdownMenuItem>
                )}
              </DropdownMenuGroup>
              <DropdownMenuSeparator />

              <DropdownMenuGroup>
                <DropdownMenuItem variant="destructive" onClick={handleDelete}>
                  <TrashIcon />
                  Törlés
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </ItemActions>
      </Item>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        <TorrentDetail
          icon={<HardDriveDownloadIcon />}
          value={formatFilesize(torrent.downloaded)}
        />
        <TorrentDetail
          icon={<ArrowBigDownIcon className="text-green-500" />}
          value={formatFilesize(torrent.downloadSpeed)}
        />
        <TorrentDetail
          icon={<HardDriveUploadIcon className="size-4" />}
          value={formatFilesize(torrent.uploaded)}
        />
        <TorrentDetail
          icon={<ArrowBigUpIcon className="text-destructive" />}
          value={formatFilesize(torrent.uploadSpeed)}
        />
        <TorrentDetail
          icon={<HardDriveIcon />}
          value={formatFilesize(torrent.total)}
        />
      </div>
    </div>
  )
}
