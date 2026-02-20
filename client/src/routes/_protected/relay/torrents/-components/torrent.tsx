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
  LayersPlusIcon,
  PinIcon,
  PinOffIcon,
  PlayIcon,
  RotateCcwIcon,
  TrashIcon,
} from 'lucide-react'
import type { JSX, MouseEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Badge } from '@/shared/components/ui/badge'
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
import { assertExists, formatDateTime, parseApiError } from '@/shared/lib/utils'
import { useDeleteTorrent, useUpdateTorrent } from '@/shared/queries/torrents'
import { getTrackers } from '@/shared/queries/trackers'
import { formatFilesize } from '@/shared/utils/file.util'

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

  const { getTrackerLabel, getTrackerUrl, getTrackerFullDownload } =
    useMetadata()

  const confirmDialog = useConfirmDialog()

  const { mutateAsync: updateTorrent } = useUpdateTorrent(torrent.infoHash)
  const { mutateAsync: deleteTorrent } = useDeleteTorrent()

  const tracker = useMemo(
    () => trackers.find((t) => t.tracker === torrent.tracker)!,
    [trackers],
  )

  const fullDownload = useMemo(() => {
    if (torrent.fullDownload === null) {
      return tracker.downloadFullTorrent
    }

    return torrent.fullDownload
  }, [torrent, tracker])

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

    try {
      await updateTorrent({ isPersisted: !torrent.isPersisted })
    } catch (error) {
      const message = parseApiError(error)
      toast.error(message)
    }
  }

  const handleOpenDetails: MouseEventHandler<HTMLDivElement> = (e) => {
    e.stopPropagation()

    const trackerUrl = getTrackerUrl(torrent.tracker)

    const detailsPath = trackerUrl.detailsPath.replace(
      '{torrentId}',
      torrent.torrentId,
    )
    const url = new URL(detailsPath, trackerUrl.url)

    window.open(url.href, '_blank', 'noopener,noreferrer')
  }

  const handleFullDownload =
    (value: boolean | null): MouseEventHandler<HTMLDivElement> =>
    async (e) => {
      e.stopPropagation()

      try {
        await updateTorrent({ fullDownload: value })
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
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

              {!getTrackerFullDownload(torrent.tracker) && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuGroup>
                    {fullDownload ? (
                      <DropdownMenuItem onClick={handleFullDownload(false)}>
                        <FileDownIcon />
                        Részleges letöltés
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
                </>
              )}
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
      <div className="mt-1 flex flex-wrap gap-2">
        <Badge
          variant="secondary"
          title={`Torrent hozzáadás időpontja: ${formatDateTime(torrent.createdAt)}`}
        >
          <LayersPlusIcon />
          {formatDateTime(torrent.createdAt)}
        </Badge>
        <Badge
          variant="secondary"
          title={`Torrent utolsó lejátszásának időpontja: ${formatDateTime(torrent.lastPlayedAt)}`}
        >
          <PlayIcon />
          {formatDateTime(torrent.lastPlayedAt)}
        </Badge>
        {torrent.isPersisted && (
          <Badge
            variant="secondary"
            title="Aktív seedben tartás, a torrent nem törlődik autómatikusan."
          >
            <PinIcon />
          </Badge>
        )}
      </div>
    </div>
  )
}
