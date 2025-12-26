import { useForm } from '@tanstack/react-form'
import { useQueries } from '@tanstack/react-query'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  onlyBestTorrentSchema,
  torrentLanguagesSchema,
  torrentResolutionsSchema,
  torrentSeedSchema,
  torrentVideoQualitiesSchema,
} from '@/common/schemas'
import { LanguagesSelector } from '@/shared/components/form/languages-selector'
import { ResolutionsSelector } from '@/shared/components/form/resolutions-selector'
import { VideoQualitiesSelector } from '@/shared/components/form/video-qualities-selector'
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
import { getMetadata } from '@/shared/queries/metadata'

export const validatorSchema = z.object({
  torrentResolutions: torrentResolutionsSchema,
  torrentVideoQualities: torrentVideoQualitiesSchema,
  torrentLanguages: torrentLanguagesSchema,
  torrentSeed: torrentSeedSchema,
  onlyBestTorrent: onlyBestTorrentSchema,
})

export function TorrentsPreferences() {
  const [{ data: me }, { data: metadata }] = useQueries({
    queries: [getMe, getMetadata],
  })
  assertExists(me)
  assertExists(metadata)

  const { mutateAsync: updateMe } = useUpdateMe()

  const form = useForm({
    defaultValues: {
      torrentLanguages: me.torrentLanguages,
      torrentVideoQualities: me.torrentVideoQualities,
      torrentResolutions: me.torrentResolutions,
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
    <div className="columns-1 md:columns-2 gap-4">
      <Card className="break-inside-avoid mb-4">
        <CardHeader>
          <CardTitle>Előnyben részesített felbontás</CardTitle>
          <CardDescription>
            Állítsd be, milyen felbontást részesítsen előnyben a rendszer.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form.Field name="torrentResolutions" mode="array">
            {(field) => (
              <ResolutionsSelector
                items={field.state.value}
                onChangeItems={(items) => field.handleChange(items)}
              />
            )}
          </form.Field>
        </CardContent>
      </Card>
      <Card className="break-inside-avoid mb-4">
        <CardHeader>
          <CardTitle>Előnyben részesített képminőség</CardTitle>
          <CardDescription>
            Állítsd be, milyen képminőséget részesítsen előnyben a rendszer.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form.Field name="torrentVideoQualities" mode="array">
            {(field) => (
              <VideoQualitiesSelector
                items={field.state.value}
                onChangeItems={(items) => field.handleChange(items)}
              />
            )}
          </form.Field>
        </CardContent>
      </Card>
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
      <Card className="break-inside-avoid mb-4">
        <CardHeader>
          <CardTitle>Torrent elérhetősége</CardTitle>
          <CardDescription>
            Kevés seeder esetén, akadozhat a lejátszás, mennyi seeder alatt
            legyen rejtve a torrent?
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
                    <Label htmlFor={seedOption.value}>{seedOption.label}</Label>
                  </div>
                ))}
              </RadioGroup>
            )}
          </form.Field>
        </CardContent>
      </Card>
      <Card className="break-inside-avoid mb-4">
        <CardHeader>
          <CardTitle>Családbarát mód</CardTitle>
          <CardDescription>
            Csak a legjobb torrent jelenik meg a beállított preferenciáid
            alapján - így nem kell listából válogatni.
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
    </div>
  )
}
