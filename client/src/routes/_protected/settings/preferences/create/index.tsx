import { useQueries } from '@tanstack/react-query'
import { Link, createFileRoute, useNavigate } from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { toast } from 'sonner'

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldLabel,
  FieldTitle,
} from '@/shared/components/ui/field'
import { RadioGroup, RadioGroupItem } from '@/shared/components/ui/radio-group'
import { Separator } from '@/shared/components/ui/separator'
import { useAppForm } from '@/shared/contexts/form-context'
import type { PreferenceEnum } from '@/shared/lib/source-client'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import type { PreferenceDto } from '@/shared/queries/me-preferences'
import {
  getMePreferences,
  useCreateMePreference,
} from '@/shared/queries/me-preferences'
import { getMetadata } from '@/shared/queries/metadata'

import { PreferenceForm } from '../-features/preference-form/preference-form'

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

  const activatePreferences = mePreferences.map(
    (mePreference) => mePreference.preference,
  )
  const availablePreferences = preferences.filter(
    (preference) => !activatePreferences.includes(preference.value),
  )

  const { mutateAsync: createMePreference } = useCreateMePreference()

  const form = useAppForm({
    defaultValues: {
      preference: availablePreferences[0].value,
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
        <Card>
          <CardHeader>
            <CardTitle>Preferencia konfiguráció létrehozása</CardTitle>
            <CardDescription>
              Válaszd ki milyen preferencia konfigurációt szeretnél létrehozni
              és végezd el a konfigurációt.
            </CardDescription>
          </CardHeader>
          <Separator />
          <CardContent className="grid gap-6">
            <form.Field name="preference">
              {(field) => (
                <div className="grid gap-2">
                  <RadioGroup
                    value={field.state.value}
                    onValueChange={(value: PreferenceEnum) => {
                      form.reset()
                      field.setValue(value)
                    }}
                  >
                    {availablePreferences.map((preference) => (
                      <FieldLabel htmlFor={preference.value}>
                        <Field orientation="horizontal">
                          <FieldContent>
                            <FieldTitle>{preference.label}</FieldTitle>
                            <FieldDescription>
                              For individuals and small teams.
                            </FieldDescription>
                          </FieldContent>
                          <RadioGroupItem
                            value={preference.value}
                            id={preference.value}
                          />
                        </Field>
                      </FieldLabel>
                    ))}
                  </RadioGroup>
                </div>
              )}
            </form.Field>
            <Separator />
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
                  Létrehozás
                </form.SubscribeButton>
              )}
            </form.Subscribe>
          </CardFooter>
        </Card>
      </form>
    </form.AppForm>
  )
}
