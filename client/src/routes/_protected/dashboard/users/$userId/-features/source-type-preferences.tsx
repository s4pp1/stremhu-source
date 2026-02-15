import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'
import * as z from 'zod'

import { torrentSourceTypesSchema } from '@/common/schemas'
import { SourceTypesSelector } from '@/shared/components/form/source-types-selector'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import type { UserDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUpdateUser } from '@/shared/queries/users'

const validatorSchema = z.object({
  torrentSourceTypes: torrentSourceTypesSchema,
})

type SourceTypePreferences = {
  user: UserDto
}

export function SourceTypePreferences(props: SourceTypePreferences) {
  const { user } = props

  const { mutateAsync: updateUser } = useUpdateUser()

  const form = useForm({
    defaultValues: {
      torrentSourceTypes: user.torrentSourceTypes,
    },
    validators: {
      onChange: validatorSchema,
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
        await updateUser({ userId: user.id, payload: value })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return (
    <Card className="break-inside-avoid mb-4">
      <CardHeader>
        <CardTitle>Előnyben részesített forrás</CardTitle>
        <CardDescription>
          Állítsd be, milyen forrást részesítsen előnyben a rendszer.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <form.Field name="torrentSourceTypes" mode="array">
          {(field) => (
            <SourceTypesSelector
              items={field.state.value}
              onChangeItems={(items) => field.handleChange(items)}
            />
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
