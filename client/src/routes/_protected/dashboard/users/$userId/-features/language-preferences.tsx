import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'
import * as z from 'zod'

import { torrentLanguagesSchema } from '@/common/schemas'
import { LanguagesSelector } from '@/shared/components/form/languages-selector'
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
  torrentLanguages: torrentLanguagesSchema,
})

type LanguagePreferences = {
  user: UserDto
}

export function LanguagePreferences(props: LanguagePreferences) {
  const { user } = props

  const { mutateAsync: updateUser } = useUpdateUser()

  const form = useForm({
    defaultValues: {
      torrentLanguages: user.torrentLanguages,
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
        <CardTitle>Előnyben részesített nyelv</CardTitle>
        <CardDescription>
          Állítsd be, milyen nyelvet részesítsen előnyben a rendszer.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form.Field name="torrentLanguages" mode="array">
          {(field) => (
            <LanguagesSelector
              items={field.state.value}
              onChangeItems={(items) => field.handleChange(items)}
            />
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
