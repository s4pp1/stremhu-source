import { useQueries } from '@tanstack/react-query'
import {
  Link,
  createFileRoute,
  useNavigate,
  useParams,
} from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { toast } from 'sonner'

import { PreferenceForm } from '@/features/preference-form/preference-form'
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { useAppForm } from '@/shared/contexts/form-context'
import type { PreferenceCreateRequest } from '@/shared/lib/source/source-client'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import {
  getUserPreference,
  useUpdateUserPreference,
} from '@/shared/queries/users'

export const Route = createFileRoute(
  '/_protected/dashboard/users/$userId/preferences/$preferenceId/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const navigate = useNavigate()
  const { userId, preferenceId } = useParams({
    from: '/_protected/dashboard/users/$userId/preferences/$preferenceId/',
  })

  const [{ data: userPreference }] = useQueries({
    queries: [getUserPreference(userId, preferenceId)],
  })
  assertExists(userPreference)

  const { mutateAsync: updateUserPreference } = useUpdateUserPreference(
    userId,
    preferenceId,
  )

  const form = useAppForm({
    defaultValues: {
      preferenceId: userPreference.id,
      attributeIds: userPreference.attributes.map((attribute) => attribute.id),
    } as PreferenceCreateRequest,
    onSubmit: async ({ value }) => {
      try {
        await updateUserPreference(value)
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
      <form className="grid gap-4" onSubmit={onSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="capitalize">{userPreference.name}</span>{' '}
              konfigurációja
            </CardTitle>
          </CardHeader>
          <Separator />
          <CardContent className="grid gap-4">
            <PreferenceForm form={form} preference={userPreference} />
          </CardContent>
          <CardFooter className="gap-4 justify-end">
            <form.SubscribeButton asChild variant="outline">
              <Link
                to="/dashboard/users/$userId/preferences"
                params={{ userId }}
              >
                Mégsem
              </Link>
            </form.SubscribeButton>
            <form.Subscribe
              selector={(state) => {
                const disabled = state.values.attributeIds.length === 0
                return disabled
              }}
            >
              {(disabled) => (
                <form.SubscribeButton type="submit" disabled={disabled}>
                  Módosítás
                </form.SubscribeButton>
              )}
            </form.Subscribe>
          </CardFooter>
        </Card>
      </form>
    </form.AppForm>
  )
}
