import { useForm } from '@tanstack/react-form'
import { useSuspenseQuery } from '@tanstack/react-query'
import { isEmpty } from 'lodash'
import { useMemo } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'
import { t } from '@lingui/core/macro'
import { Trans } from '@lingui/react/macro'

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
import { parseApiError } from '@/shared/lib/utils'
import { getRelaySettings, useUpdateRelaySetting } from '@/shared/queries/relay'

const schema = z.object({
  downloadLimit: z.coerce.number<string>().positive().nullable(),
  uploadLimit: z.coerce.number<string>().positive().nullable(),
})

export function Speed() {
  const { data: relaySettings } = useSuspenseQuery(getRelaySettings)

  const { mutateAsync: updateSetting } = useUpdateRelaySetting()

  const setting = useMemo(() => {
    let downloadLimit = null
    if (relaySettings.downloadLimit !== 0) {
      downloadLimit = `${relaySettings.downloadLimit / 125_000}`
    }

    let uploadLimit = null
    if (relaySettings.uploadLimit !== 0) {
      uploadLimit = `${relaySettings.uploadLimit / 125_000}`
    }

    return {
      downloadLimit,
      uploadLimit,
    }
  }, [relaySettings])

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
        // Download limit
        let downloadLimit = 0

        if (value.downloadLimit !== null) {
          downloadLimit = Number(value.downloadLimit) * 125_000
        }

        // Upload limit
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
        <CardTitle><Trans>Speed</Trans></CardTitle>
        <CardDescription>
          <Trans>Maximum download and upload speed. Leave empty for unlimited.</Trans>
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-6">
        <form.Field name="downloadLimit">
          {(field) => (
            <Field>
              <FieldLabel><Trans>Download</Trans></FieldLabel>
              <InputGroup>
                <InputGroupInput
                  placeholder={t`No limit`}
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
                      field.handleChange(value)
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
              <FieldLabel><Trans>Upload</Trans></FieldLabel>
              <InputGroup>
                <InputGroupInput
                  placeholder={t`No limit`}
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
