import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'
import * as z from 'zod'
import { Trans } from '@lingui/react/macro'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import type { UserResponse } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUserUpdate } from '@/shared/queries/users'
import { onlyBestTorrentSchema } from '@/shared/schemas'

const validatorSchema = z.object({
  onlyBestTorrent: onlyBestTorrentSchema,
})

type OnlyBestTorrent = {
  user: UserResponse
}

export function OnlyBestTorrent(props: OnlyBestTorrent) {
  const { user } = props

  const { mutateAsync: updateUser } = useUserUpdate()

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
        <CardTitle><Trans>Family friendly mode</Trans></CardTitle>
        <CardDescription>
          <Trans>Only the best torrent is displayed based on your preferences - so you don't have to pick from a list.</Trans>
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
              <Trans>Family friendly mode</Trans>
            </Label>
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
