import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'
import * as z from 'zod'

import { onlyBestTorrentSchema } from '@/common/schemas'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import type { UserDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUpdateUser } from '@/shared/queries/users'

const validatorSchema = z.object({
  onlyBestTorrent: onlyBestTorrentSchema,
})

type OnlyBestTorrent = {
  user: UserDto
}

export function OnlyBestTorrent(props: OnlyBestTorrent) {
  const { user } = props

  const { mutateAsync: updateUser } = useUpdateUser()

  const form = useForm({
    defaultValues: {
      onlyBestTorrent: user.onlyBestTorrent,
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
        <CardTitle>Családbarát mód</CardTitle>
        <CardDescription>
          Csak a legjobb torrent jelenik meg a beállított preferenciáid alapján
          - így nem kell listából válogatni.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form.Field name="onlyBestTorrent">
          {(field) => (
            <Label htmlFor={field.name} className="flex items-start gap-3">
              <Switch
                id={field.name}
                checked={field.state.value}
                onCheckedChange={field.handleChange}
              />
              Családbarát mód
            </Label>
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
