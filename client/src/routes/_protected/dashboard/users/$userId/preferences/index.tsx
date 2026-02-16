import { useQuery } from '@tanstack/react-query'
import { createFileRoute, useParams } from '@tanstack/react-router'

import { assertExists } from '@/shared/lib/utils'
import { getUser } from '@/shared/queries/users'

import { OnlyBestTorrent } from '../-features/only-best-torrent'
import { TorrentSeeders } from '../-features/torrent-seeders'

export const Route = createFileRoute(
  '/_protected/dashboard/users/$userId/preferences/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const { userId } = useParams({
    from: '/_protected/dashboard/users/$userId/preferences/',
  })
  const { data: user } = useQuery(getUser(userId))
  assertExists(user)

  return (
    <div className="columns-1 md:columns-2 gap-4">
      <div className="break-inside-avoid mb-4">
        <TorrentSeeders user={user} />
      </div>
      <div className="break-inside-avoid mb-4">
        <OnlyBestTorrent user={user} />
      </div>
    </div>
  )
}
