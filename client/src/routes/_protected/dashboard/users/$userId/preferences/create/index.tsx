import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useNavigate, useParams } from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { CreatePreference } from '@/features/create-preference/create-preference'
import { useAppForm } from '@/shared/contexts/form-context'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'
import {
  getUserPreferences,
  useCreateUserPreference,
} from '@/shared/queries/user-preferences'
import type { PreferenceDto } from '@/shared/type/preference.dto'

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

  const [{ data: metadata }, { data: userPreferences }] = useQueries({
    queries: [getMetadata, getUserPreferences(userId)],
  })
  assertExists(metadata)
  assertExists(userPreferences)

  const { preferences } = metadata

  const availablePrefs = useMemo(() => {
    const currentPrefs = userPreferences.map(
      (mePreference) => mePreference.preference,
    )
    const prefs = preferences.filter(
      (preference) => !currentPrefs.includes(preference.value),
    )

    return prefs
  }, [userPreferences, preferences])

  const { mutateAsync: createUserPreference } = useCreateUserPreference(userId)

  const form = useAppForm({
    defaultValues: {
      preference: availablePrefs[0].value,
      preferred: [],
      blocked: [],
    } as PreferenceDto,
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
