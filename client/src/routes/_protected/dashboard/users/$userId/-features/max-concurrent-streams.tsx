import { useForm } from '@tanstack/react-form'
import { isEmpty } from 'lodash'
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
import { Field, FieldError } from '@/shared/components/ui/field'
import { InputGroup, InputGroupInput } from '@/shared/components/ui/input-group'
import type { UserResponse } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUserUpdate } from '@/shared/queries/users'

const schema = z.object({
  maxConcurrentStreams: z.coerce.number<string>().min(1).nullable(),
})

type MaxConcurrentStreamsProps = {
  user: UserResponse
}

export function MaxConcurrentStreams(props: MaxConcurrentStreamsProps) {
  const { user } = props

  const { mutateAsync: updateUser } = useUserUpdate()

  const form = useForm({
    defaultValues: {
      maxConcurrentStreams: user.maxConcurrentStreams?.toString() ?? null,
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
        await updateUser({
          userId: user.id,
          payload: {
            maxConcurrentStreams: value.maxConcurrentStreams
              ? Number(value.maxConcurrentStreams)
              : null,
          },
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
        <CardTitle><Trans>Limit concurrent streams</Trans></CardTitle>
        <CardDescription>
          <Trans>Limit the maximum number of concurrent streams. Leave empty for unlimited.</Trans>
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-6">
        <form.Field name="maxConcurrentStreams">
          {(field) => (
            <Field>
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
