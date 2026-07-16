import { useSuspenseQueries } from '@tanstack/react-query'
import {
  Link,
  createFileRoute,
  useNavigate,
  useParams,
} from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { toast } from 'sonner'
import { Trans } from '@lingui/react/macro'

import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import {
  getMePreference,
  getMePreferenceDefinition,
  useUpdateMePreference,
} from '@/shared/queries/me'

import { PreferenceForm } from '../../../../../features/preference-form/preference-form'

export const Route = createFileRoute(
  '/_protected/settings/preferences/$preferenceId/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const navigate = useNavigate()
  const { preferenceId } = useParams({
    from: '/_protected/settings/preferences/$preferenceId/',
  })

  const [{ data: preference }, { data: mePreference }] = useSuspenseQueries({
    queries: [
      getMePreference(preferenceId),
      getMePreferenceDefinition(preferenceId),
    ],
  })

  const { mutateAsync: updateMePreference } = useUpdateMePreference(
    mePreference.id,
  )

  const form = useAppForm({
    defaultValues: {
      preferenceId: mePreference.id,
      attributeIds: mePreference.attributes.map((attribute) => attribute.id),
    },
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
              <Trans>
                <span className="capitalize">{mePreference.name}</span> configuration
              </Trans>
            </CardTitle>
          </CardHeader>
          <Separator />
          <CardContent className="grid gap-4">
            <PreferenceForm form={form} preference={preference} />
          </CardContent>
          <CardFooter className="gap-4 justify-end">
            <form.SubscribeButton asChild variant="outline">
              <Link to="/settings/preferences"><Trans>Cancel</Trans></Link>
            </form.SubscribeButton>
            <form.Subscribe
              selector={(state) => {
                const disabled = state.values.attributeIds.length === 0
                return disabled
              }}
            >
              {(disabled) => (
                <form.SubscribeButton type="submit" disabled={disabled}>
                  <Trans>Update</Trans>
                </form.SubscribeButton>
              )}
            </form.Subscribe>
          </CardFooter>
        </Card>
      </form>
    </form.AppForm>
  )
}
