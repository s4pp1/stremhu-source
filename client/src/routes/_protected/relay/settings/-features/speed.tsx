import { useForm } from '@tanstack/react-form'
import { useQueryClient } from '@tanstack/react-query'
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
import { Field, FieldError, FieldLabel } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from '@/shared/components/ui/input-group'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getRelaySettings, useUpdateRelaySetting } from '@/shared/queries/relay'

const schema = z.object({
  downloadLimit: z.coerce.number<string>().positive().nullable(),
  uploadLimit: z.coerce.number<string>().positive().nullable(),
})

export function Speed() {
  const queryClient = useQueryClient()

  const relay = queryClient.getQueryData(getRelaySettings.queryKey)
  assertExists(relay)

  const { mutateAsync: updateSetting } = useUpdateRelaySetting()

  const setting = useMemo(() => {
    let downloadLimit = null
    if (relay.downloadLimit !== 0) {
      downloadLimit = `${relay.downloadLimit / 125_000}`
    }

    let uploadLimit = null
    if (relay.uploadLimit !== 0) {
      uploadLimit = `${relay.uploadLimit / 125_000}`
    }

    return {
      downloadLimit,
      uploadLimit,
    }
  }, [relay])

  const form = useForm({
    defaultValues: {
      downloadLimit: setting.downloadLimit,
      uploadLimit: setting.uploadLimit,
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
        // Letöltési sebesség
        let downloadLimit = 0

        if (value.downloadLimit !== null) {
          downloadLimit = Number(value.downloadLimit) * 125_000
        }

        // Feltöltési sebesség
        let uploadLimit = 0

        if (value.uploadLimit !== null) {
          uploadLimit = Number(value.uploadLimit) * 125_000
        }

        await updateSetting({
          downloadLimit,
          uploadLimit,
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
        <CardTitle>Sebesség</CardTitle>
        <CardDescription>
          Maximális letöltési és feltöltési sebesség. Ha üresen hagyod korlátlan
          lesz.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-6">
        <form.Field name="downloadLimit">
          {(field) => (
            <Field>
              <FieldLabel>Letöltés</FieldLabel>
              <InputGroup>
                <InputGroupInput
                  placeholder="Nincs limitálva"
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
                  <InputGroupText>Mbit/s</InputGroupText>
                </InputGroupAddon>
              </InputGroup>
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
        <form.Field name="uploadLimit">
          {(field) => (
            <Field>
              <FieldLabel>Feltöltés</FieldLabel>
              <InputGroup>
                <InputGroupInput
                  placeholder="Nincs limitálva"
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
                  <InputGroupText>Mbit/s</InputGroupText>
                </InputGroupAddon>
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
