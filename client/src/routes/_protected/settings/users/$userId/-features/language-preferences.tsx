import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { userPreferencesSchema } from '@/common/schemas'
import { LanguagesSelector } from '@/shared/components/form/languages-selector'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import type { LanguageEnum, UserDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUpdateProfile } from '@/shared/queries/users'

type LanguagePreferences = {
  user: UserDto
}

export function LanguagePreferences(props: LanguagePreferences) {
  const { user } = props

  const { mutateAsync: updateProfile } = useUpdateProfile()

  const form = useForm({
    defaultValues: {
      torrentLanguages: user.torrentLanguages,
      torrentResolutions: user.torrentResolutions,
      torrentSeed: user.torrentSeed,
    },
    validators: {
      onChange: userPreferencesSchema,
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
        await updateProfile({ userId: user.id, payload: value })
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
              onAdd={(language) => {
                field.pushValue(language)
              }}
              onDelete={(language) => {
                const index = field.state.value.findIndex(
                  (value) => value === language,
                )
                field.removeValue(index)
              }}
              onSortableDragEnd={(event) => {
                const { active, over } = event

                if (!over || active.id === over.id) return
                const oldIndex = field.state.value.indexOf(
                  active.id as LanguageEnum,
                )
                const newIndex = field.state.value.indexOf(
                  over.id as LanguageEnum,
                )
                if (oldIndex < 0 || newIndex < 0) return
                field.moveValue(oldIndex, newIndex)
              }}
            />
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
