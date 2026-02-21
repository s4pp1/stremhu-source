import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Field, FieldError } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from '@/shared/components/ui/input-group'
import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getSettings, useUpdateSetting } from '@/shared/queries/settings'

const schema = z.object({
  hitAndRun: z.boolean(),
  keepSeed: z.coerce
    .number<string>('Csak szám adható meg')
    .positive('Csak pozitív szám adható meg.')
    .nullable(),
})

export function KeepSeeding() {
  const { data: setting } = useQuery(getSettings)
  assertExists(setting)

  const { mutateAsync: updateSetting } = useUpdateSetting()

  const keepSeedDays = useMemo(() => {
    if (setting.keepSeedSeconds > 0) {
      const days = setting.keepSeedSeconds / (24 * 60 * 60)
      return `${days}`
    }

    return null
  }, [setting.keepSeedSeconds])

  const form = useForm({
    defaultValues: {
      hitAndRun: setting.hitAndRun,
      keepSeed: keepSeedDays,
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 1000,
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        let keepSeedSeconds = 0

        if (value.keepSeed) {
          const days = Number(value.keepSeed)
          keepSeedSeconds = days * 24 * 60 * 60
        }

        await updateSetting({
          keepSeedSeconds,
          hitAndRun: value.hitAndRun,
        })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Automatikus torrent törlés</CardTitle>
        <CardDescription>
          Minden nap hajnalban lefut az ellenőrzés, de torrent csak akkor kerül
          törlésre, ha a beállított feltételek mindegyike teljesül.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <form.Field name="hitAndRun">
          {(field) => (
            <div className="grid gap-1">
              <Label htmlFor={field.name} className="flex items-start gap-3">
                <p className="flex-1 text-sm leading-none font-medium">
                  Hit'n'Run alapú törlés
                </p>
                <Switch
                  id={field.name}
                  checked={field.state.value}
                  onCheckedChange={field.handleChange}
                />
              </Label>
              <p className="text-muted-foreground text-sm">
                Ellenőrzi a tracker oldal alapján a teljesítést és csak ezt
                követően törlődhet.
              </p>
            </div>
          )}
        </form.Field>
        <div className="grid gap-3">
          <form.Field name="keepSeed">
            {(field) => (
              <div className="grid gap-3">
                <div className="grid gap-1">
                  <Label
                    htmlFor={field.name}
                    className="flex items-start gap-3"
                  >
                    <p className="flex-1 text-sm leading-none font-medium">
                      Lejátszás alapú törlés
                    </p>
                    <Switch
                      id={field.name}
                      checked={field.state.value !== null}
                      onCheckedChange={(checked) => {
                        field.setValue(checked ? '4' : null)
                      }}
                    />
                  </Label>
                  <p className="text-muted-foreground text-sm">
                    A torrent csak akkor törlődhet, ha a legutóbbi lejátszás óta
                    eltelt a beállított idő.
                  </p>
                </div>
                {field.state.value !== null && (
                  <Field>
                    <InputGroup>
                      <InputGroupInput
                        placeholder="Hány nap után engedje?"
                        inputMode="numeric"
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => {
                          field.handleChange(e.target.value)
                        }}
                      />
                      <InputGroupAddon align="inline-end">
                        <InputGroupText>nap után</InputGroupText>
                      </InputGroupAddon>
                    </InputGroup>
                    {field.state.meta.isTouched && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )}
              </div>
            )}
          </form.Field>
        </div>
      </CardContent>
    </Card>
  )
}
