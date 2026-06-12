import { useSuspenseQueries } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { PlusIcon } from 'lucide-react'

import { Preference } from '@/features/preferences/preference'
import { PreferencesSection } from '@/features/preferences/preferences-section'
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
import {
  getMeAttributeExclusions,
  getMePreferenceDefinitions,
  getMePreferences,
  useDeleteMePreference,
  useReorderMePreference,
} from '@/shared/queries/me'

import { OtherPreferences } from './-features/other-preferences'

export const Route = createFileRoute('/_protected/settings/preferences/')({
  component: RouteComponent,
})

function RouteComponent() {
  const [
    { data: mePreferences },
    { data: mePreferenceDefinitions },
    { data: meAttributeExclusions },
  ] = useSuspenseQueries({
    queries: [
      getMePreferences(),
      getMePreferenceDefinitions(),
      getMeAttributeExclusions(),
    ],
  })

  const { mutateAsync: reorderMePreference } = useReorderMePreference()
  const { mutateAsync: deleteMePreference } = useDeleteMePreference()

  const handleReorder = async (preferenceIds: string[]) => {
    await reorderMePreference({
      preferenceIds,
    })
  }

  const handleDelete = async (preference: PreferenceResponse) => {
    await deleteMePreference(preference.id)
  }

  return (
    <div className="grid gap-8">
      <Card className="break-inside-avoid mb-4">
        <CardHeader>
          <CardTitle>Kizárt tulajdonságok</CardTitle>
          <CardDescription>
            Amennyiben a torrent tartalmazza a kizárt tulajdonságot, az nem fog
            megjelenni a listában.
          </CardDescription>
          <CardAction>
            <Button size="icon-sm" className="rounded-full">
              <PlusIcon />
            </Button>
          </CardAction>
        </CardHeader>
        <Separator />
        <CardContent className="flex flex-wrap gap-2">
          {meAttributeExclusions.map((meAttributeExclusion) => (
            <Badge variant="destructive" key={meAttributeExclusion.id}>
              {meAttributeExclusion.name}
            </Badge>
          ))}
        </CardContent>
      </Card>
      <Separator />
      <PreferencesSection
        toCreateLink={{ to: '/settings/preferences/create' }}
        preferences={mePreferences}
        currentPreferences={mePreferenceDefinitions}
        renderPreference={(preference) => (
          <Preference
            preference={preference}
            toEditLink={{
              to: '/settings/preferences/$preferenceId',
              params: { preferenceId: preference.id },
            }}
            onDelete={handleDelete}
          />
        )}
        onReorder={handleReorder}
      />
      <Separator />
      <OtherPreferences />
    </div>
  )
}
