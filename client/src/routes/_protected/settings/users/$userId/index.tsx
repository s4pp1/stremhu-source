import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useParams } from '@tanstack/react-router'

import { assertExists } from '@/shared/lib/utils'
import { getUser } from '@/shared/queries/users'

import { LanguagePreferences } from './-features/language-preferences'
import { OnlyBestTorrent } from './-features/only-best-torrent'
import { ResolutionPreferences } from './-features/resolution-preferences'
import { TorrentSeeders } from './-features/torrent-seeders'
import { UserProfile } from './-features/user-profile'
import { VideoQualityPreferences } from './-features/video-quality-preferences'

export const Route = createFileRoute('/_protected/settings/users/$userId/')({
  component: UserRoute,
})

function UserRoute() {
  const { userId } = useParams({ from: '/_protected/settings/users/$userId' })

  const [{ data: user }] = useQueries({
    queries: [getUser(userId)],
  })
  assertExists(user)

  return (
    <div className="columns-1 md:columns-2 gap-4">
      <div className="break-inside-avoid mb-4">
        <UserProfile user={user} />
      </div>
      <div className="break-inside-avoid mb-4">
        <LanguagePreferences user={user} />
      </div>
      <div className="break-inside-avoid mb-4">
        <ResolutionPreferences user={user} />
      </div>
      <div className="break-inside-avoid mb-4">
        <VideoQualityPreferences user={user} />
      </div>
      <div className="break-inside-avoid mb-4">
        <TorrentSeeders user={user} />
      </div>
      <div className="break-inside-avoid mb-4">
        <OnlyBestTorrent user={user} />
      </div>
    </div>
  )
}
