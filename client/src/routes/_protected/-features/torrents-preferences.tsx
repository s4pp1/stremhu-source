import { useForm } from '@tanstack/react-form'
import { useQueries } from '@tanstack/react-query'
import { toast } from 'sonner'

import { userPreferencesSchema } from '@/common/schemas'
import { LanguagesSelector } from '@/shared/components/form/languages-selector'
import { ResolutionsSelector } from '@/shared/components/form/resolutions-selector'
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
import type { LanguageEnum, ResolutionEnum } from '@/shared/lib/source-client'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMe, useUpdateMe } from '@/shared/queries/me'
import { getMetadata } from '@/shared/queries/metadata'

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
      torrentSeed: me.torrentSeed,
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
          <CardTitle>Előnyben részesített képminőség</CardTitle>
          <CardDescription>
            Állítsd be, milyen képminőséget részesítsen előnyben a rendszer.
          </CardDescription>
        </CardHeader>
        <CardContent>
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
    </div>
  )
}
