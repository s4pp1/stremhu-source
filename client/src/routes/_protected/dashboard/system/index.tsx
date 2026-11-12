import { createFileRoute } from '@tanstack/react-router'

import { Separator } from '@/shared/components/ui/separator'

import { Indexers } from './-features/indexers'
import { KeepSeeding } from './-features/keep-seeding'
import { NetworkAccessInfo } from './-features/network-access-info'
import { Restart } from './-features/restart'
import { TorrentFilesCache } from './-features/torrent-files-cache'

export const Route = createFileRoute('/_protected/dashboard/system/')({
  component: SystemRoute,
})

function SystemRoute() {
  return (
    <div className="grid gap-8">
      <Indexers />
      <Separator />
      <div className="grid items-start gap-4 md:grid-cols-2">
        <div className="grid gap-4">
          <NetworkAccessInfo />
          <TorrentFilesCache />
        </div>
        <div className="grid gap-4">
          <KeepSeeding />
          <Restart />
        </div>
      </div>
    </div>
  )
}
