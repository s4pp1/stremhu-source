import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { isEmpty } from 'lodash'
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
import {
  Item,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
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
    if (setting.keepSeedSeconds) {
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
        let keepSeedSeconds = null

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
        <CardTitle>Torrent törlés feltételei</CardTitle>
        <CardDescription>
          A torrent és a hozzá tartozó adat csak akkor törlődik, ha a bekapcsolt
          feltételek mindegyike teljesül.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <form.Field name="hitAndRun">
          {(field) => (
            <Label htmlFor={field.name} className="flex items-start gap-3">
              <Switch
                id={field.name}
                checked={field.state.value}
                onCheckedChange={field.handleChange}
              />
              <div className="flex-1 grid gap-2 font-normal">
                <p className="text-sm leading-none font-medium">
                  Hit'n'Run ellenőrzés
                </p>
                <p className="text-muted-foreground text-sm">
                  Minden nap hajnalban ellenőrzi, hogy melyik torrent
                  teljesítette.
                </p>
              </div>
            </Label>
          )}
        </form.Field>
        <div className="grid gap-3">
          <Item variant="default" className="p-0">
            <ItemContent>
              <ItemTitle>Lejátszás alapú seedben tartás</ItemTitle>
              <ItemDescription>
                Az utolsó lejátszást követően mennyi ideig tartsa seedben a
                torrentet?
              </ItemDescription>
            </ItemContent>
          </Item>
          <form.Field name="keepSeed">
            {(field) => (
              <Field>
                <InputGroup>
                  <InputGroupInput
                    placeholder="Nincs seedben tartás"
                    inputMode="numeric"
                    id={field.name}
                    name={field.name}
                    value={field.state.value ?? ''}
                    onBlur={field.handleBlur}
                    onChange={(e) => {
                      const value = e.target.value

                      if (isEmpty(value)) {
                        field.handleChange(null)
                      } else {
                        field.handleChange(e.target.value)
                      }
                    }}
                  />
                  <InputGroupAddon align="inline-end">
                    <InputGroupText>nap</InputGroupText>
                  </InputGroupAddon>
                </InputGroup>
                {field.state.meta.isTouched && (
                  <FieldError errors={field.state.meta.errors} />
                )}
              </Field>
            )}
          </form.Field>
        </div>
      </CardContent>
    </Card>
  )
}
