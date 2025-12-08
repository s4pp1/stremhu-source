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
import {
  Item,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Label } from '@/shared/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/shared/components/ui/radio-group'
import { SEED_OPTIONS } from '@/shared/constants'
import type { LanguageEnum, ResolutionEnum } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { getMe, useUpdateMePreferences } from '@/shared/queries/me'
import { getMetadata } from '@/shared/queries/metadata'

export function TorrentsPreferences() {
  const [{ data: me }, { data: metadata }] = useQueries({
    queries: [getMe, getMetadata],
  })

  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)
  if (!me) throw new Error(`Nincs "me" a cache-ben`)

  const { mutateAsync: updatePreferences } = useUpdateMePreferences()

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
      onChangeDebounceMs: 2000,
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updatePreferences(value)
        toast.success('Módosítások elmentve')
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Preferenciák</CardTitle>
        <CardDescription>
          Konfiguráld, hogy a Stremio-ban megjelenő torrenteknél mik a
          preferenciáid és ennek megfelelően fognak megjelenni.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Filmek, sorozatok nyelve</ItemTitle>
            <ItemDescription>
              Állítsd be, milyen nyelvű tartalmak jelenjenek meg.
            </ItemDescription>
            <form.Field name="torrentLanguages" mode="array">
              {(field) => (
                <LanguagesSelector
                  className="mt-2"
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
          </ItemContent>
        </Item>
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Filmek, sorozatok minősége</ItemTitle>
            <ItemDescription>
              Állítsd be, milyen minőségű tartalmak jelenjenek meg.
            </ItemDescription>
            <form.Field name="torrentResolutions" mode="array">
              {(field) => (
                <ResolutionsSelector
                  className="mt-2"
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
          </ItemContent>
        </Item>
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Torrent elérhetősége</ItemTitle>
            <ItemDescription>
              Kevés seeder esetén, akadozhat a lejátszás, mennyi seeder alatt
              legyen rejtve a torrent?
            </ItemDescription>
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
          </ItemContent>
        </Item>
      </CardContent>
    </Card>
  )
}
