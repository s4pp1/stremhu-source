import { useForm } from '@tanstack/react-form'
import { useQueries } from '@tanstack/react-query'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  torrentAudioCodecsSchema,
  torrentLanguagesSchema,
  torrentResolutionsSchema,
  torrentSourceTypesSchema,
  torrentVideoQualitiesSchema,
} from '@/common/schemas'
import { AudioCodecsSelector } from '@/shared/components/form/audio-codecs-selector'
import { LanguagesSelector } from '@/shared/components/form/languages-selector'
import { ResolutionsSelector } from '@/shared/components/form/resolutions-selector'
import { SourceTypesSelector } from '@/shared/components/form/source-types-selector'
import { VideoQualitiesSelector } from '@/shared/components/form/video-qualities-selector'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMe, useUpdateMe } from '@/shared/queries/me'
import { getMetadata } from '@/shared/queries/metadata'

export const validatorSchema = z.object({
  torrentResolutions: torrentResolutionsSchema,
  torrentVideoQualities: torrentVideoQualitiesSchema,
  torrentAudioCodecs: torrentAudioCodecsSchema,
  torrentSourceTypes: torrentSourceTypesSchema,
  torrentLanguages: torrentLanguagesSchema,
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
      torrentResolutions: me.torrentResolutions,
      torrentVideoQualities: me.torrentVideoQualities,
      torrentAudioCodecs: me.torrentAudioCodecs,
      torrentSourceTypes: me.torrentSourceTypes,
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
          <CardTitle>Előnyben részesített forrás</CardTitle>
          <CardDescription>
            Állítsd be, milyen forrást részesítsen előnyben a rendszer.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form.Field name="torrentSourceTypes" mode="array">
            {(field) => (
              <SourceTypesSelector
                items={field.state.value}
                onChangeItems={(items) => field.handleChange(items)}
              />
            )}
          </form.Field>
        </CardContent>
      </Card>
      <Card className="break-inside-avoid mb-4">
        <CardHeader>
          <CardTitle>Előnyben részesített hangminőség</CardTitle>
          <CardDescription>
            Állítsd be, milyen hangminőséget részesítsen előnyben a rendszer.
          </CardDescription>
        </CardHeader>
        <CardContent>
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
    </div>
  )
}
