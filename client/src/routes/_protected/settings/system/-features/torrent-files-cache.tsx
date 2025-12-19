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
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getSettings, useUpdateSetting } from '@/shared/queries/settings'

const schema = z.object({
  cacheRetention: z.coerce.number<string>().positive().nullable(),
})

export function TorrentFilesCache() {
  const { data: setting } = useQuery(getSettings)
  assertExists(setting)

  const { mutateAsync: updateSetting } = useUpdateSetting()

  const cacheRetentionDays = useMemo(() => {
    if (setting.cacheRetentionSeconds) {
      const days = setting.cacheRetentionSeconds / (24 * 60 * 60)
      return `${days}`
    }

    return null
  }, [setting.cacheRetentionSeconds])

  const form = useForm({
    defaultValues: {
      cacheRetention: cacheRetentionDays,
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
        let cacheRetentionSeconds = null

        if (value.cacheRetention) {
          const days = Number(value.cacheRetention)
          cacheRetentionSeconds = days * 24 * 60 * 60
        }

        await updateSetting({
          cacheRetentionSeconds,
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
        <CardTitle>Cache kezelés</CardTitle>
        <CardDescription>
          Az alkalmazás a gyorsabb működés érdekében tárolja a torrent fájlokat,
          konfiguráld milyen gyakran távolítse el azokat, ha nincsenek
          használva.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form.Field name="cacheRetention">
          {(field) => (
            <Field>
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
                  <InputGroupText>nap</InputGroupText>
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
