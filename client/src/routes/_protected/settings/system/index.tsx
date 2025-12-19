import { createFileRoute } from '@tanstack/react-router'

import { Separator } from '@/shared/components/ui/separator'

import { KeepSeeding } from './-features/keep-seeding'
import { NetworkAccessInfo } from './-features/network-access-info'
import { StremhuCatalogInfo } from './-features/stremhu-catalog-info'
import { TorrentFilesCache } from './-features/torrent-files-cache'
import { Trackers } from './-features/trackers'

export const Route = createFileRoute('/_protected/settings/system/')({
  component: SystemRoute,
})

function SystemRoute() {
  return (
    <div className="grid gap-8">
      <div className="columns-1 md:columns-2 gap-4">
        <div className="break-inside-avoid mb-4">
          <NetworkAccessInfo />
        </div>
        <div className="break-inside-avoid mb-4">
          <StremhuCatalogInfo />
        </div>
        <div className="break-inside-avoid mb-4">
          <TorrentFilesCache />
        </div>
        <div>
          <KeepSeeding />
        </div>
      </div>
      <Separator />
      <Trackers />
    </div>
  )
}
