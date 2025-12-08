import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'

import { userPreferencesSchema } from '@/common/schemas'
import { LanguagesSelector } from '@/shared/components/form/languages-selector'
import { ResolutionsSelector } from '@/shared/components/form/resolutions-selector'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Item, ItemContent, ItemTitle } from '@/shared/components/ui/item'
import { Label } from '@/shared/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/shared/components/ui/radio-group'
import { SEED_OPTIONS } from '@/shared/constants'
import type {
  LanguageEnum,
  ResolutionEnum,
  UserDto,
} from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'
import { useUpdateProfile } from '@/shared/queries/users'

interface UserPreferencesProps {
  user: UserDto
}

export function UserPreferences(props: UserPreferencesProps) {
  const { user } = props

  const { data: metadata } = useQuery(getMetadata)
  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)

  const { mutateAsync: updateProfile } = useUpdateProfile()

  const form = useForm({
    defaultValues: {
      torrentLanguages: user.torrentLanguages,
      torrentResolutions: user.torrentResolutions,
      torrentSeed: user.torrentSeed,
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
        await updateProfile({ userId: user.id, payload: value })
        toast.success('Módosítások elmentve')
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
        <CardTitle>Preferenciák</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Filmek, sorozatok nyelve</ItemTitle>
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
        <form.Field name="torrentResolutions" mode="array">
          {(field) => (
            <Item variant="default" className="p-0">
              <ItemContent>
                <ItemTitle>Filmek, sorozatok minősége</ItemTitle>
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
              </ItemContent>
            </Item>
          )}
        </form.Field>

        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Torrent elrejtése</ItemTitle>
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
