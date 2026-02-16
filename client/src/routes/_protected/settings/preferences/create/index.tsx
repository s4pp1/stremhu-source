import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { CreatePreference } from '@/features/create-preference/create-preference'
import { useAppForm } from '@/shared/contexts/form-context'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import {
  getMePreferences,
  useCreateMePreference,
} from '@/shared/queries/me-preferences'
import { getMetadata } from '@/shared/queries/metadata'
import type { PreferenceDto } from '@/shared/type/preference.dto'

export const Route = createFileRoute(
  '/_protected/settings/preferences/create/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const navigate = useNavigate()

  const [{ data: metadata }, { data: mePreferences }] = useQueries({
    queries: [getMetadata, getMePreferences],
  })
  assertExists(metadata)
  assertExists(mePreferences)

  const { preferences } = metadata

  const availablePrefs = useMemo(() => {
    const currentPrefs = mePreferences.map(
      (mePreference) => mePreference.preference,
    )
    const prefs = preferences.filter(
      (preference) => !currentPrefs.includes(preference.value),
    )

    return prefs
  }, [mePreferences, preferences])

  const { mutateAsync: createMePreference } = useCreateMePreference()

  const form = useAppForm({
    defaultValues: {
      preference: availablePrefs[0].value,
      preferred: [],
      blocked: [],
    } as PreferenceDto,
    onSubmit: async ({ value }) => {
      try {
        await createMePreference(value)
        navigate({ to: '/settings/preferences' })
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const onSubmit: SubmitEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  return (
    <form.AppForm>
      <form onSubmit={onSubmit}>
        <CreatePreference
          form={form}
          preferences={availablePrefs}
          toBackLink={{ to: '/settings/preferences' }}
        />
      </form>
    </form.AppForm>
  )
}
