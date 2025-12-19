import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { userPreferencesSchema } from '@/common/schemas'
import { ResolutionsSelector } from '@/shared/components/form/resolutions-selector'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import type { ResolutionEnum, UserDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUpdateUser } from '@/shared/queries/users'

type MediaQualityPreferences = {
  user: UserDto
}

export function MediaQualityPreferences(props: MediaQualityPreferences) {
  const { user } = props

  const { mutateAsync: updateUser } = useUpdateUser()

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
      onChangeDebounceMs: 2000,
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateUser({ userId: user.id, payload: value })
        toast.success('Módosítások elmentve')
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
        <CardTitle>Előnyben részesített képminőség</CardTitle>
        <CardDescription>
          Állítsd be, milyen képminőséget részesítsen előnyben a rendszer.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <form.Field name="torrentResolutions" mode="array">
          {(field) => (
            <ResolutionsSelector
              items={field.state.value}
              onAdd={(resolution) => {
                field.pushValue(resolution)
              }}
              onDelete={(resolution) => {
                const index = field.state.value.findIndex(
                  (value) => value === resolution,
                )
                field.removeValue(index)
              }}
              onSortableDragEnd={(event) => {
                const { active, over } = event

                if (!over || active.id === over.id) return
                const oldIndex = field.state.value.indexOf(
                  active.id as ResolutionEnum,
                )
                const newIndex = field.state.value.indexOf(
                  over.id as ResolutionEnum,
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
