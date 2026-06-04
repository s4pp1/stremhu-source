import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { CreatePreference } from '@/features/create-preference/create-preference'
import { useAppForm } from '@/shared/contexts/form-context'
import type { PreferenceCreateRequest } from '@/shared/lib/source/source-client'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMePreferences, useCreateMePreference } from '@/shared/queries/me'
import { getPreferences } from '@/shared/queries/preferences'

export const Route = createFileRoute(
  '/_protected/settings/preferences/create/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const navigate = useNavigate()

  const [{ data: preferences }, { data: mePreferences }] = useQueries({
    queries: [getPreferences, getMePreferences()],
  })
  assertExists(preferences)
  assertExists(mePreferences)

  const availablePrefs = useMemo(() => {
    const currentPrefs = mePreferences.map((mePreference) => mePreference.id)
    const prefs = preferences.filter(
      (preference) => !currentPrefs.includes(preference.id),
    )

    return prefs
  }, [mePreferences, preferences])

  if (availablePrefs.length === 0) {
    return navigate({ to: '/settings/preferences' })
  }

  const { mutateAsync: createMePreference } = useCreateMePreference()

  const form = useAppForm({
    defaultValues: {
      preferenceId: availablePrefs[0].id,
      attributeIds: [],
    } as PreferenceCreateRequest,
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
