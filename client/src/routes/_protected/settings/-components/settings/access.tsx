import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import * as z from 'zod'

import { parseApiError } from '@/common/utils'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { getSettings, useUpdateSetting } from '@/queries/settings'

const accessOptions = [
  {
    label: 'Hozzáférés otthoni hálózaton',
    description: (
      <>
        Otthoni hálózaton eléri a Stremio az addont a{' '}
        <a
          className="underline italic "
          href="https://local-ip.medicmobile.org/"
          target="_blank"
        >
          https://local-ip.medicmobile.org/
        </a>{' '}
        segítségével.
      </>
    ),
    value: 'true',
  },
  {
    label: 'Távoli hozzáférés egyedi domain-al',
    description: (
      <>
        Saját domain használata, biztosítva a https kapcsolat.{' '}
        <a
          className="underline italic "
          href="https://www.noip.com/"
          target="_blank"
        >
          https://www.noip.com/
        </a>
      </>
    ),
    value: 'false',
  },
]

const schema = z.object({
  endpoint: z
    .url({ protocol: /^https$/, error: 'Csak HTTPS engedélyezett' })
    .superRefine((value, ctx) => {
      const parseUrl = new URL(value)
      const lastCharacter = value.substring(value.length - 1)

      const noPath = parseUrl.pathname === '/' && lastCharacter !== '/'

      if (!noPath || parseUrl.search || parseUrl.hash) {
        ctx.addIssue({
          code: 'custom',
          message: 'Nem tartalmazhat elérési utat, query-t vagy fragmentet',
        })
      }
    }),
  enebledlocalIp: z.boolean(),
})

export function Access() {
  const { data: setting } = useQuery(getSettings)
  if (!setting) throw new Error(`Nincs "settings" a cache-ben`)

  const { mutateAsync: updateSetting } = useUpdateSetting()

  const form = useForm({
    defaultValues: {
      endpoint: '',
      enebledlocalIp: setting.enebledlocalIp,
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 2000,
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateSetting(value)
        toast.success('Módosítások elmentve')
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return (
    <form name="setting">
      <Card>
        <CardHeader>
          <CardTitle>Hozzáférés</CardTitle>
          <CardDescription>
            A Stremio csak HTTPS kapcsolatot fogad el az addon telepítéshez. A
            Stremio integráció az itt beállított domain-t használja.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <form.Field name="enebledlocalIp">
            {(field) => (
              <RadioGroup
                value={field.state.value.toString()}
                onValueChange={(value) => {
                  const booleanValue = value === 'true'
                  field.handleChange(booleanValue)
                }}
              >
                {accessOptions.map((accessOption) => (
                  <div
                    key={accessOption.value}
                    className="flex items-start gap-3"
                  >
                    <RadioGroupItem
                      value={accessOption.value}
                      id={accessOption.value}
                    />
                    <div className="grid gap-2">
                      <Label htmlFor={accessOption.value}>
                        {accessOption.label}
                      </Label>
                      <p className="text-muted-foreground text-sm">
                        {accessOption.description}
                      </p>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            )}
          </form.Field>
          <form.Field name="endpoint">
            {(field) => (
              <Field>
                <FieldLabel>Addon URL</FieldLabel>
                <Input
                  name={field.name}
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => {
                    field.handleChange(e.target.value)
                  }}
                  placeholder="https://stremhu.yourdomain.com"
                />
                <FieldDescription>
                  Otthoni hálózat esetén példál:{' '}
                  <span className="font-mono font-bold">
                    https://192-168-1-5.local-ip.medicmobile.org:3443
                  </span>
                </FieldDescription>
                {field.state.meta.isTouched && (
                  <FieldError errors={field.state.meta.errors} />
                )}
              </Field>
            )}
          </form.Field>
        </CardContent>
      </Card>
    </form>
  )
}
