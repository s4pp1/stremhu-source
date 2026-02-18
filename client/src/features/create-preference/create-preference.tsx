import type { LinkProps } from '@tanstack/react-router'
import { Link } from '@tanstack/react-router'

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
import type { PreferenceEnum } from '@/shared/lib/source-client'
import type { PreferenceMetaDto } from '@/shared/type/preference-meta.dto'
import { capitalizeFirstLetter } from '@/shared/utils/text.util'

import { PreferenceForm } from '../preference-form/preference-form'
import { preferenceFormValues } from '../preference-form/preference-form-values'

export const CreatePreference = withForm({
  props: {
    preferences: [] as Array<PreferenceMetaDto>,
    toBackLink: {} as LinkProps,
  },
  defaultValues: preferenceFormValues,
  render: ({ form, preferences, toBackLink }) => {
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
                  {preferences.map((preference) => (
                    <FieldLabel htmlFor={preference.value}>
                      <Field orientation="horizontal">
                        <FieldContent>
                          <FieldTitle>
                            {capitalizeFirstLetter(preference.label)}
                          </FieldTitle>
                          <FieldDescription>
                            {preference.description}
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
            <Link {...toBackLink}>Mégsem</Link>
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
    )
  },
})
