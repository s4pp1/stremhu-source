import { useForm } from '@tanstack/react-form'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Field, FieldError, FieldLabel } from '@/shared/components/ui/field'
import { InputGroup, InputGroupInput } from '@/shared/components/ui/input-group'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getRelaySettings, useUpdateRelaySetting } from '@/shared/queries/relay'

const schema = z.object({
  connectionsLimit: z.coerce.number<string>().min(1),
  torrentConnectionsLimit: z.coerce.number<string>().min(1),
})

export function Connection() {
  const queryClient = useQueryClient()

  const setting = queryClient.getQueryData(getRelaySettings.queryKey)
  assertExists(setting)

  const { mutateAsync: updateSetting } = useUpdateRelaySetting()

  const form = useForm({
    defaultValues: {
      connectionsLimit: setting.connectionsLimit.toString(),
      torrentConnectionsLimit: setting.torrentConnectionsLimit.toString(),
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
        await updateSetting({
          ...value,
          connectionsLimit: value.connectionsLimit
            ? Number(value.connectionsLimit)
            : 0,
          torrentConnectionsLimit: value.torrentConnectionsLimit
            ? Number(value.torrentConnectionsLimit)
            : 0,
        })
        toast.success('Módosítások elmentve')
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
        <CardTitle>Kapcsolat</CardTitle>
        <CardDescription>Kapcsolatok számának limitálása.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-6">
        <form.Field name="connectionsLimit">
          {(field) => (
            <Field>
              <FieldLabel>Globális kapcsolatok maximális száma</FieldLabel>
              <InputGroup>
                <InputGroupInput
                  inputMode="numeric"
                  id={field.name}
                  name={field.name}
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => {
                    field.handleChange(e.target.value)
                  }}
                />
              </InputGroup>
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
        <form.Field name="torrentConnectionsLimit">
          {(field) => (
            <Field>
              <FieldLabel>
                Torrentenkénti kapcsolatok maximális száma
              </FieldLabel>
              <InputGroup>
                <InputGroupInput
                  inputMode="numeric"
                  id={field.name}
                  name={field.name}
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => {
                    field.handleChange(e.target.value)
                  }}
                />
              </InputGroup>
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
