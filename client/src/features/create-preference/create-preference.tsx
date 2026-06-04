import type { LinkProps } from '@tanstack/react-router'
import { Link } from '@tanstack/react-router'
import { upperFirst } from 'lodash'

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
import { withForm } from '@/shared/contexts/form-context'
import type { PreferenceResponse } from '@/shared/lib/source/source-client'

import { PreferenceForm } from '../preference-form/preference-form'
import { preferenceFormValues } from '../preference-form/preference-form-values'

export const CreatePreference = withForm({
  props: {
    preferences: [] as PreferenceResponse[],
    toBackLink: {} as LinkProps,
  },
  defaultValues: preferenceFormValues,
  render: ({ form, preferences, toBackLink }) => {
    const preferenceMap = preferences.reduce<
      Record<string, PreferenceResponse>
    >((acc, preference) => {
      acc[preference.id] = preference
      return acc
    }, {})

    return (
      <Card>
        <CardHeader>
          <CardTitle>Preferencia konfiguráció létrehozása</CardTitle>
          <CardDescription>
            Válaszd ki milyen preferencia konfigurációt szeretnél létrehozni és
            végezd el a konfigurációt.
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="grid gap-6">
          <form.Field name="preferenceId">
            {(field) => (
              <div className="grid gap-2">
                <RadioGroup
                  value={field.state.value}
                  onValueChange={(value) => {
                    form.reset()
                    field.setValue(value)
                  }}
                >
                  {preferences.map((preference) => (
                    <FieldLabel htmlFor={preference.id}>
                      <Field orientation="horizontal">
                        <FieldContent>
                          <FieldTitle>{upperFirst(preference.name)}</FieldTitle>
                          <FieldDescription>
                            {preference.description}
                          </FieldDescription>
                        </FieldContent>
                        <RadioGroupItem
                          value={preference.id}
                          id={preference.id}
                        />
                      </Field>
                    </FieldLabel>
                  ))}
                </RadioGroup>
              </div>
            )}
          </form.Field>
          <Separator />
          <form.Subscribe selector={(state) => state.values.preferenceId}>
            {(preferenceId) => (
              <PreferenceForm
                form={form}
                preference={preferenceMap[preferenceId]}
              />
            )}
          </form.Subscribe>
        </CardContent>
        <CardFooter className="gap-4 justify-end">
          <form.SubscribeButton asChild variant="outline">
            <Link {...toBackLink}>Mégsem</Link>
          </form.SubscribeButton>
          <form.Subscribe
            selector={(state) => {
              const disabled = state.values.attributeIds.length === 0
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
    )
  },
})
