import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'
import * as z from 'zod'

import { torrentSeedSchema } from '@/common/schemas'
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
import type { UserDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUpdateUser } from '@/shared/queries/users'

const validatorSchema = z.object({
  torrentSeed: torrentSeedSchema,
})

type TorrentSeeders = {
  user: UserDto
}

export function TorrentSeeders(props: TorrentSeeders) {
  const { user } = props

  const { mutateAsync: updateUser } = useUpdateUser()

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
        <CardTitle>Torrent elérhetősége</CardTitle>
        <CardDescription>
          Kevés seeder esetén, akadozhat a lejátszás, mennyi seeder alatt legyen
          rejtve a torrent?
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
