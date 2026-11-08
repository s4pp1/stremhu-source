import { useQueries } from '@tanstack/react-query'
import { toast } from 'sonner'
import * as z from 'zod'

import { SmartFilterSettings } from '@/features/smart-filter/smart-filter-settings'
import { SubtitleSettingsCard } from '@/features/subtitle-settings/subtitle-settings'
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
import { useAppForm } from '@/shared/contexts/form-context'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMe, useUpdateMe } from '@/shared/queries/me'
import {
  enableCatalogSearchSchema,
  enableSmartFilterSchema,
  enableStreamDeduplicationSchema,
  smartFilterGroupingPreferenceIdSchema,
  smartFilterLimitSchema,
  torrentSeedSchema,
} from '@/shared/schemas'

export const validatorSchema = z.object({
  torrentSeed: torrentSeedSchema,
  enableSmartFilter: enableSmartFilterSchema,
  enableStreamDeduplication: enableStreamDeduplicationSchema,
  smartFilterGroupingPreferenceId: smartFilterGroupingPreferenceIdSchema,
  smartFilterLimit: smartFilterLimitSchema,
  enableCatalogSearch: enableCatalogSearchSchema,
})

export function OtherPreferences() {
  const [{ data: me }] = useQueries({
    queries: [getMe()],
  })
  assertExists(me)

  const { mutateAsync: updateMe } = useUpdateMe()

  const form = useAppForm({
    defaultValues: {
      torrentSeed: me.torrentSeed,
      enableSmartFilter: me.enableSmartFilter,
      enableStreamDeduplication: me.enableStreamDeduplication,
      smartFilterGroupingPreferenceId: me.smartFilterGroupingPreferenceId,
      smartFilterLimit: me.smartFilterLimit,
      enableCatalogSearch: me.enableCatalogSearch,
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
        <CardTitle>További preferenciák</CardTitle>
        <CardDescription>
          Itt finomhangolhatod a torrent-találatok megjelenését (pl. elrejtés
          kevés seeder esetén), és bekapcsolhatod a Családbarát módot a
          tisztább, egyszerűbb listához.
        </CardDescription>
      </CardHeader>
      <div className="columns-1 md:columns-2 gap-4">
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
            <CardTitle>Találatok összevonása</CardTitle>
            <CardDescription>
              Több tracker (pl. nCore, HunTorrent, Majomparádé) azonos tartalmú
              release-einek intelligens összevonása egyetlen találattá,
              összesített seederekkel.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form.Field name="enableStreamDeduplication">
              {(field) => (
                <Label
                  htmlFor={field.name}
                  className="flex items-center gap-3 cursor-pointer"
                >
                  <Switch
                    id={field.name}
                    checked={field.state.value}
                    onCheckedChange={field.handleChange}
                  />
                  <span>Több-trackeres találatok összevonása</span>
                </Label>
              )}
            </form.Field>
          </CardContent>
        </Card>

        <Card className="break-inside-avoid mb-4">
          <CardHeader>
            <CardTitle>Katalógus keresés</CardTitle>
            <CardDescription>
              A Stremio és Nuvio közvetlen keresőmezőjének kiszolgálása a
              trackerek torrent-katalógusából. A változás azonnal érvényes, az
              addont nem kell újratelepíteni. Kikapcsolva a szerver nem ad
              katalógustalálatot és nem terheli a trackereket; a StremHU
              keresési sora a kliensben üresen megjelenhet.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form.Field name="enableCatalogSearch">
              {(field) => (
                <Label
                  htmlFor={field.name}
                  className="flex items-center gap-3 cursor-pointer"
                >
                  <Switch
                    id={field.name}
                    checked={field.state.value}
                    onCheckedChange={field.handleChange}
                  />
                  <span>Közvetlen Stremio katalógus-keresés engedélyezése</span>
                </Label>
              )}
            </form.Field>
          </CardContent>
        </Card>

        <SmartFilterSettings
          form={form}
          fields={{
            enableSmartFilter: 'enableSmartFilter',
            smartFilterLimit: 'smartFilterLimit',
            smartFilterGroupingPreferenceId: 'smartFilterGroupingPreferenceId',
          }}
        />

        <SubtitleSettingsCard />
      </div>
    </div>
  )
}
