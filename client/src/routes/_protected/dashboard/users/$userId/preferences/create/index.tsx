import { useSuspenseQueries } from '@tanstack/react-query'
import {
  Navigate,
  createFileRoute,
  useNavigate,
  useParams,
} from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { CreatePreference } from '@/features/create-preference/create-preference'
import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import {
  getUserPreferenceDefinitions,
  getUserPreferences,
  useCreateUserPreferenceDefinition,
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

  const [{ data: preferences }, { data: preferencesDefinitions }] =
    useSuspenseQueries({
      queries: [
        getUserPreferences(userId),
        getUserPreferenceDefinitions(userId),
      ],
    })

  const availablePreferences = useMemo(() => {
    const currentPreferenceDefinitions = preferencesDefinitions.map(
      (preferenceDefinition) => preferenceDefinition.id,
    )
    const prefs = preferences.filter(
      (preference) => !currentPreferenceDefinitions.includes(preference.id),
    )

    return prefs
  }, [preferences, preferencesDefinitions])

  if (availablePreferences.length === 0) {
    return (
      <Navigate to="/dashboard/users/$userId/preferences" params={{ userId }} />
    )
  }

  const { mutateAsync: createUserPreference } =
    useCreateUserPreferenceDefinition(userId)

  const form = useAppForm({
    defaultValues: {
      preferenceId: availablePreferences[0].id,
      attributeIds: [] as string[],
    },
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
          preferences={availablePreferences}
          toBackLink={{
            to: '/dashboard/users/$userId/preferences',
            params: { userId },
          }}
        />
      </form>
    </form.AppForm>
  )
}
