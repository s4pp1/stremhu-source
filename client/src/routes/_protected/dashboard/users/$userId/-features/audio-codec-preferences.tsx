import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'
import * as z from 'zod'

import { torrentAudioCodecsSchema } from '@/common/schemas'
import { AudioCodecsSelector } from '@/shared/components/form/audio-codecs-selector'
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
  torrentAudioCodecs: torrentAudioCodecsSchema,
})

type AudioCodecPreferences = {
  user: UserDto
}

export function AudioCodecPreferences(props: AudioCodecPreferences) {
  const { user } = props

  const { mutateAsync: updateUser } = useUpdateUser()

  const form = useForm({
    defaultValues: {
      torrentAudioCodecs: user.torrentAudioCodecs,
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
        <CardTitle>Előnyben részesített hangminőség</CardTitle>
        <CardDescription>
          Állítsd be, milyen hangminőséget részesítsen előnyben a rendszer.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <form.Field name="torrentAudioCodecs" mode="array">
          {(field) => (
            <AudioCodecsSelector
              items={field.state.value}
              onChangeItems={(items) => field.handleChange(items)}
            />
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
