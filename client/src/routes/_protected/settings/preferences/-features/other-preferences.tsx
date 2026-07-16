import { useForm } from '@tanstack/react-form'
import { useQueries } from '@tanstack/react-query'
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
import { Switch } from '@/shared/components/ui/switch'
import { SEED_OPTIONS } from '@/shared/constants'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMe, useUpdateMe } from '@/shared/queries/me'
import { onlyBestTorrentSchema, torrentSeedSchema } from '@/shared/schemas'

export const validatorSchema = z.object({
  torrentSeed: torrentSeedSchema,
  onlyBestTorrent: onlyBestTorrentSchema,
})

export function OtherPreferences() {
  const [{ data: me }] = useQueries({
    queries: [getMe()],
  })
  assertExists(me)

  const { mutateAsync: updateMe } = useUpdateMe()

  const form = useForm({
    defaultValues: {
      torrentSeed: me.torrentSeed,
      onlyBestTorrent: me.onlyBestTorrent,
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
        await updateMe(value)
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return (
    <div className="grid gap-4">
      <CardHeader className="px-0">
        <CardTitle><Trans>Other preferences</Trans></CardTitle>
        <CardDescription>
          <Trans>Here you can fine-tune the appearance of torrent results (e.g. hide when there are few seeders), and turn on Family-friendly mode for a cleaner, simpler list.</Trans>
        </CardDescription>
      </CardHeader>
      <div className="columns-1 md:columns-2 gap-4">
        <Card className="break-inside-avoid mb-4">
          <CardHeader>
            <CardTitle><Trans>Torrent availability</Trans></CardTitle>
            <CardDescription>
              <Trans>With few seeders, playback might stutter. Below how many seeders should the torrent be hidden?</Trans>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form.Field name="torrentSeed">
              {(field) => (
                <RadioGroup
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
                    <div
                      key={seedOption.value}
                      className="flex items-center gap-3"
                    >
                      <RadioGroupItem
                        value={seedOption.value}
                        id={seedOption.value}
                      />
                      <Label htmlFor={seedOption.value}>
                        {seedOption.label}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              )}
            </form.Field>
          </CardContent>
        </Card>
        <Card className="break-inside-avoid mb-4">
          <CardHeader>
            <CardTitle><Trans>Family-friendly mode</Trans></CardTitle>
            <CardDescription>
              <Trans>Only the best torrent appears based on your set preferences - so you don't have to choose from a list.</Trans>
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
                  <Trans>Family-friendly mode</Trans>
                </Label>
              )}
            </form.Field>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
