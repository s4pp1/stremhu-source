import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'

import { Preference } from '@/features/preferences/preference'
import { PreferencesSection } from '@/features/preferences/preferences-section'
import { Separator } from '@/shared/components/ui/separator'
import type { PreferenceEnum } from '@/shared/lib/source-client'
import { assertExists } from '@/shared/lib/utils'
import {
  getMePreferences,
  useDeleteMePreference,
  useReorderMePreference,
} from '@/shared/queries/me-preferences'
import type { PreferenceDto } from '@/shared/type/preference.dto'

import { OtherPreferences } from './-features/other-preferences'

export const Route = createFileRoute('/_protected/settings/preferences/')({
  component: RouteComponent,
})

function RouteComponent() {
  const { data: mePreferences } = useQuery(getMePreferences)
  assertExists(mePreferences)

  const { mutateAsync: reorderMePreference } = useReorderMePreference()
  const { mutateAsync: deleteMePreference } = useDeleteMePreference()

  const handleReorder = async (preferences: Array<PreferenceEnum>) => {
    await reorderMePreference({
      preferences,
    })
  }

  const handleDelete = async (preference: PreferenceDto) => {
    await deleteMePreference(preference.preference)
  }

  return (
    <div className="grid gap-8">
      <PreferencesSection
        toCreateLink={{ to: '/settings/preferences/create' }}
        preferences={mePreferences}
        renderPreference={(preference) => (
          <Preference
            preference={preference}
            toEditLink={{
              to: '/settings/preferences/$preference',
              params: { preference: preference.preference },
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
