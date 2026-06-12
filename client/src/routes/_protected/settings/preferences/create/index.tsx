import { useSuspenseQueries } from '@tanstack/react-query'
import { Navigate, createFileRoute, useNavigate } from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { CreatePreference } from '@/features/create-preference/create-preference'
import { useAppForm } from '@/shared/contexts/form-context'
import type { PreferenceCreateRequest } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'
import {
  getMePreferenceDefinitions,
  getMePreferences,
  useCreateMePreference,
} from '@/shared/queries/me'

export const Route = createFileRoute(
  '/_protected/settings/preferences/create/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const navigate = useNavigate()

  const [{ data: mePreferences }, { data: mePreferenceDefinitions }] =
    useSuspenseQueries({
      queries: [getMePreferences(), getMePreferenceDefinitions()],
    })

  const availablePreferences = useMemo(() => {
    const currentPrefs = mePreferenceDefinitions.map(
      (mePreference) => mePreference.id,
    )
    const preferences = mePreferences.filter(
      (preference) => !currentPrefs.includes(preference.id),
    )

    return preferences
  }, [mePreferences, mePreferenceDefinitions])

  if (availablePreferences.length === 0) {
    return <Navigate to="/settings/preferences" />
  }

  const { mutateAsync: createMePreference } = useCreateMePreference()

  const form = useAppForm({
    defaultValues: {
      preferenceId: availablePreferences[0].id,
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
          preferences={availablePreferences}
          toBackLink={{ to: '/settings/preferences' }}
        />
      </form>
    </form.AppForm>
  )
}
