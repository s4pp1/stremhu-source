import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useParams } from '@tanstack/react-router'

import { Preference } from '@/features/preferences/preference'
import { PreferencesSection } from '@/features/preferences/preferences-section'
import { Separator } from '@/shared/components/ui/separator'
import type { PreferenceEnum } from '@/shared/lib/source-client'
import { assertExists } from '@/shared/lib/utils'
import {
  getUserPreferences,
  useDeleteUserPreference,
  useReorderUserPreference,
} from '@/shared/queries/user-preferences'
import { getUser } from '@/shared/queries/users'
import type { PreferenceDto } from '@/shared/type/preference.dto'

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
  const [{ data: user }, { data: userPreferences }] = useQueries({
    queries: [getUser(userId), getUserPreferences(userId)],
  })
  assertExists(user)
  assertExists(userPreferences)

  const { mutateAsync: reorderUserPreference } =
    useReorderUserPreference(userId)
  const { mutateAsync: deleteUserPreference } = useDeleteUserPreference(userId)

  const handleReorder = async (preferences: Array<PreferenceEnum>) => {
    await reorderUserPreference({
      preferences,
    })
  }

  const handleDelete = async (preference: PreferenceDto) => {
    await deleteUserPreference(preference.preference)
  }

  return (
    <div className="grid gap-8">
      <PreferencesSection
        toCreateLink={{ to: '/dashboard/users/$userId/preferences/create' }}
        preferences={userPreferences}
        renderPreference={(preference) => (
          <Preference
            preference={preference}
            toEditLink={{
              to: '/dashboard/users/$userId/preferences/$preference',
              params: { preference: preference.preference },
            }}
            onDelete={handleDelete}
          />
        )}
        onReorder={handleReorder}
      />
      <Separator />
      <div className="columns-1 md:columns-2 gap-4">
        <div className="break-inside-avoid mb-4">
          <TorrentSeeders user={user} />
        </div>
        <div className="break-inside-avoid mb-4">
          <OnlyBestTorrent user={user} />
        </div>
      </div>
    </div>
  )
}
