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
import { RadioGroup, RadioGroupItem } from '@/shared/components/ui/radio-group'
import { SEED_OPTIONS } from '@/shared/constants'
import type { UserResponse } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUserUpdate } from '@/shared/queries/users'
import { torrentSeedSchema } from '@/shared/schemas'

const validatorSchema = z.object({
  torrentSeed: torrentSeedSchema,
})

type TorrentSeedersProps = {
  user: UserResponse
}

export function TorrentSeeders(props: TorrentSeedersProps) {
  const { user } = props

  const { mutateAsync: updateUser } = useUserUpdate()

  const form = useForm({
    defaultValues: {
      torrentSeed: user.torrentSeed,
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
        <CardTitle><Trans>Torrent availability</Trans></CardTitle>
        <CardDescription>
          <Trans>In case of low seeders, playback might stutter. Under how many seeders should the torrent be hidden?</Trans>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <form.Field name="torrentSeed">
          {(field) => (
            <RadioGroup
              className="mt-2"
              value={`${field.state.value}`}
              onValueChange={(value) => {
                const number = Number(value)

                if (Number.isNaN(number)) {
                  field.setValue(null)
                } else {
                  field.setValue(number)
                }
              }}
            >
              {SEED_OPTIONS.map((seedOption) => (
                <div key={seedOption.value} className="flex items-center gap-3">
                  <RadioGroupItem
                    value={seedOption.value}
                    id={seedOption.value}
                  />
                  <Label htmlFor={seedOption.value}>{seedOption.label}</Label>
                </div>
              ))}
            </RadioGroup>
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
