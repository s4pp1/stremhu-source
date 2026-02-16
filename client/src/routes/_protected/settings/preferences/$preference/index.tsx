import { useQueries } from '@tanstack/react-query'
import {
  Link,
  createFileRoute,
  useNavigate,
  useParams,
} from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { toast } from 'sonner'

import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { useAppForm } from '@/shared/contexts/form-context'
import { useMetadata } from '@/shared/hooks/use-metadata'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import {
  getMePreference,
  useUpdateMePreference,
} from '@/shared/queries/me-preferences'
import type { PreferenceDto } from '@/shared/type/preference.dto'

import { PreferenceForm } from '../../../../../features/preference-form/preference-form'

export const Route = createFileRoute(
  '/_protected/settings/preferences/$preference/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const navigate = useNavigate()
  const { preference } = useParams({
    from: '/_protected/settings/preferences/$preference/',
  })

  const [{ data: mePreference }] = useQueries({
    queries: [getMePreference(preference)],
  })

  assertExists(mePreference)

  const { getPreference } = useMetadata()

  const preferenceMeta = getPreference(preference)

  const { mutateAsync: updateMePreference } = useUpdateMePreference()

  const form = useAppForm({
    defaultValues: {
      preference: mePreference.preference,
      preferred: mePreference.preferred,
      blocked: mePreference.blocked,
    } as PreferenceDto,
    onSubmit: async ({ value }) => {
      try {
        await updateMePreference(value)
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
      <form className="grid gap-4" onSubmit={onSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="capitalize">{preferenceMeta.label}</span>{' '}
              konfigurációja
            </CardTitle>
          </CardHeader>
          <Separator />
          <CardContent className="grid gap-4">
            <PreferenceForm form={form} />
          </CardContent>
          <CardFooter className="gap-4 justify-end">
            <form.SubscribeButton asChild variant="outline">
              <Link to="/settings/preferences">Mégsem</Link>
            </form.SubscribeButton>
            <form.Subscribe
              selector={(state) => {
                const disabled =
                  state.values.preferred.length === 0 &&
                  state.values.blocked.length === 0

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
