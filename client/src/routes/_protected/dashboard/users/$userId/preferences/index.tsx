import { useSuspenseQueries } from '@tanstack/react-query'
import { Link, createFileRoute, useParams } from '@tanstack/react-router'
import { BanIcon, EditIcon } from 'lucide-react'
import { Trans } from '@lingui/react/macro'

import { Preference } from '@/features/preferences/preference'
import { PreferencesSection } from '@/features/preferences/preferences-section'
import { Alert, AlertTitle } from '@/shared/components/ui/alert'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import type { PreferenceResponse } from '@/shared/lib/source/source-client'
import { assertExists } from '@/shared/lib/utils'
import {
  getUser,
  getUserAttributeExclusions,
  getUserPreferenceDefinitions,
  getUserPreferences,
  useDeleteUserPreference,
  useReorderUserPreference,
} from '@/shared/queries/users'

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
  const [
    { data: user },
    { data: userPreferences },
    { data: userPreferenceDefinitions },
    { data: userAttributeExclusions },
  ] = useSuspenseQueries({
    queries: [
      getUser(userId),
      getUserPreferences(userId),
      getUserPreferenceDefinitions(userId),
      getUserAttributeExclusions(userId),
    ],
  })
  assertExists(user)

  const { mutateAsync: reorderUserPreference } =
    useReorderUserPreference(userId)
  const { mutateAsync: deleteUserPreference } = useDeleteUserPreference(userId)

  const handleReorder = async (preferenceIds: string[]) => {
    await reorderUserPreference({
      preferenceIds,
    })
  }

  const handleDelete = async (preference: PreferenceResponse) => {
    await deleteUserPreference(preference.id)
  }

  return (
    <div className="grid gap-8">
      <Card className="break-inside-avoid mb-4">
        <CardHeader>
          <CardTitle><Trans>Excluded attributes</Trans></CardTitle>
          <CardDescription>
            <Trans>If the torrent contains an excluded attribute, it will not appear in the list.</Trans>
          </CardDescription>
          <CardAction>
            <Button asChild size="icon-sm" className="rounded-full">
              <Link
                to="/dashboard/users/$userId/preferences/attributes"
                params={{ userId }}
              >
                <EditIcon />
              </Link>
            </Button>
          </CardAction>
        </CardHeader>
        <Separator />
        <CardContent className="flex flex-wrap gap-2">
          {userAttributeExclusions.map((userAttributeExclusion) => (
            <Badge variant="destructive" key={userAttributeExclusion.id}>
              {userAttributeExclusion.name}
            </Badge>
          ))}
          {userAttributeExclusions.length === 0 && (
            <Alert>
              <BanIcon />
              <AlertTitle><Trans>No excluded attributes.</Trans></AlertTitle>
            </Alert>
          )}
        </CardContent>
      </Card>
      <Separator />
      <PreferencesSection
        toCreateLink={{ to: '/dashboard/users/$userId/preferences/create' }}
        preferences={userPreferences}
        currentPreferences={userPreferenceDefinitions}
        renderPreference={(preference) => (
          <Preference
            preference={preference}
            toEditLink={{
              to: '/dashboard/users/$userId/preferences/$preferenceId',
              params: { preferenceId: preference.id },
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
