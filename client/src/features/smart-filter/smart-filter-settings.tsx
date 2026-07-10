import { useSuspenseQueries } from '@tanstack/react-query'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import {
  Field,
  FieldDescription,
  FieldLabel,
} from '@/shared/components/ui/field'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Switch } from '@/shared/components/ui/switch'
import { withFieldGroup } from '@/shared/contexts/form-context'
import { getPreferences } from '@/shared/queries/preferences'

import { smartFilterFormValues } from './smart-filter-form-values'

export const SmartFilterSettings = withFieldGroup({
  defaultValues: smartFilterFormValues,
  render: ({ group }) => {
    const [{ data: preferences }] = useSuspenseQueries({
      queries: [getPreferences],
    })

    const groupablePreferences = preferences.filter(
      (preference) => preference.allowBestTorrentGrouping,
    )

    return (
      <Card className="break-inside-avoid mb-4">
        <CardHeader>
          <CardTitle>Családbarát mód</CardTitle>
          <CardDescription>
            Csak a legjobb torrentek jelennek meg a beállított preferenciáid
            alapján - így nem kell listából válogatni.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          <group.Field name="enableSmartFilter">
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
          </group.Field>

          <group.Subscribe
            selector={(state) => ({
              enableSmartFilter: state.values.enableSmartFilter,
              smartFilterLimit: state.values.smartFilterLimit,
            })}
          >
            {({ enableSmartFilter, smartFilterLimit }) =>
              enableSmartFilter && (
                <>
                  <group.Field name="smartFilterLimit">
                    {(field) => (
                      <Field>
                        <FieldLabel>Megjelenő találatok száma</FieldLabel>
                        <Input
                          type="number"
                          min={1}
                          max={50}
                          value={field.state.value}
                          onChange={(e) => {
                            const val = parseInt(e.target.value, 10)
                            if (!isNaN(val)) {
                              field.handleChange(val)
                            }
                          }}
                        />
                        <FieldDescription>
                          Maximálisan hány legjobb találat jelenjen meg?
                        </FieldDescription>
                      </Field>
                    )}
                  </group.Field>

                  {smartFilterLimit >= 2 && (
                    <group.Field name="smartFilterGroupingPreferenceId">
                      {(field) => (
                        <Field>
                          <FieldLabel>Listázás kategóriák szerint</FieldLabel>
                          <Select
                            value={field.state.value ?? 'none'}
                            onValueChange={(value) =>
                              field.handleChange(
                                value === 'none' ? null : value,
                              )
                            }
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Válassz kategóriát..." />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">Nincs</SelectItem>
                              {groupablePreferences.map(
                                (groupablePreference) => (
                                  <SelectItem
                                    key={groupablePreference.id}
                                    value={groupablePreference.id}
                                  >
                                    {groupablePreference.emoji}{' '}
                                    {groupablePreference.name}
                                  </SelectItem>
                                ),
                              )}
                            </SelectContent>
                          </Select>
                          <FieldDescription>
                            Ha beállítasz egy kategóriát, a Családbarát mód nem
                            csak a preferenciáid szerinti abszolút legjobb
                            torrentet adja vissza, hanem garantálja, hogy a
                            választott kategória különböző változataiból is
                            mindenképp megjelenjen találat.
                          </FieldDescription>
                        </Field>
                      )}
                    </group.Field>
                  )}
                </>
              )
            }
          </group.Subscribe>
        </CardContent>
      </Card>
    )
  },
})
