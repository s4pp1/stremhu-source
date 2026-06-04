import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useNavigate, useParams } from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { CreatePreference } from '@/features/create-preference/create-preference'
import { useAppForm } from '@/shared/contexts/form-context'
import type { PreferenceCreateRequest } from '@/shared/lib/source/source-client'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getPreferences } from '@/shared/queries/preferences'
import {
  getUserPreferences,
  useCreateUserPreference,
} from '@/shared/queries/users'

export const Route = createFileRoute(
  '/_protected/dashboard/users/$userId/preferences/create/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const navigate = useNavigate()
  const { userId } = useParams({
    from: '/_protected/dashboard/users/$userId/preferences/create/',
  })

  const [{ data: preferences }, { data: userPreferences }] = useQueries({
    queries: [getPreferences, getUserPreferences(userId)],
  })
  assertExists(preferences)
  assertExists(userPreferences)

  const availablePrefs = useMemo(() => {
    const currentPrefs = userPreferences.map(
      (userPreference) => userPreference.id,
    )
    const prefs = preferences.filter(
      (preference) => !currentPrefs.includes(preference.id),
    )

    return prefs
  }, [preferences, preferences])

  if (availablePrefs.length === 0) {
    return navigate({ to: '/settings/preferences' })
  }

  const { mutateAsync: createUserPreference } = useCreateUserPreference(userId)

  const form = useAppForm({
    defaultValues: {
      preferenceId: availablePrefs[0].id,
      attributeIds: [],
    } as PreferenceCreateRequest,
    onSubmit: async ({ value }) => {
      try {
        await createUserPreference(value)
        navigate({
          to: '/dashboard/users/$userId/preferences',
          params: { userId },
        })
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
          toBackLink={{
            to: '/dashboard/users/$userId/preferences',
            params: { userId },
          }}
        />
      </form>
    </form.AppForm>
  )
}
