import { useForm, useStore } from '@tanstack/react-form'
import { useQuery, useSuspenseQuery } from '@tanstack/react-query'
import { InfoIcon } from 'lucide-react'
import { useRef, useState } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { Badge } from '@/shared/components/ui/badge'
import { Field, FieldError } from '@/shared/components/ui/field'
import { Input } from '@/shared/components/ui/input'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from '@/shared/components/ui/input-group'
import { Label } from '@/shared/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Separator } from '@/shared/components/ui/separator'
import { Switch } from '@/shared/components/ui/switch'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/shared/components/ui/tooltip'
import type {
  StorageCleanupThresholdUnitEnum,
  StorageCleanupTriggerEnum,
} from '@/shared/lib/source/source-client'
import { formatDateTime, parseApiError } from '@/shared/lib/utils'
import {
  getSystemSettings,
  useSystemSettingsUpdate,
} from '@/shared/queries/system'
import { getStorageCleanupQueue } from '@/shared/queries/torrents'
import { formatFilesize } from '@/shared/utils/file.util'
import { STORAGE_CLEANUP_PROTECTED_REASON_LABELS } from '@/shared/utils/storage-cleanup.util'

const TRIGGER_LABELS: Record<StorageCleanupTriggerEnum, string> = {
  scheduled: 'Ütemezett',
  manual: 'Manuális',
}

type StorageCleanupFormValues = {
  enabled: boolean
  thresholdValue: string
  thresholdUnit: StorageCleanupThresholdUnitEnum
  minScore: string
}

const schema = z
  .object({
    enabled: z.boolean(),
    thresholdValue: z.coerce
      .number<string>('Csak szám adható meg')
      .min(0, 'Csak pozitív szám adható meg.'),
    thresholdUnit: z.enum(['percent', 'gb']),
    minScore: z.coerce
      .number<string>('Csak szám adható meg')
      .min(0, 'A pontszám nem lehet negatív.')
      .max(100, 'A pontszám legfeljebb 100 lehet.'),
  })
  .refine(
    (value) => value.thresholdUnit !== 'percent' || value.thresholdValue <= 100,
    {
      message: 'Százalék esetén legfeljebb 100 adható meg.',
      path: ['thresholdValue'],
    },
  )

export function StorageCleanupSection() {
  const { data: systemSetting } = useSuspenseQuery(getSystemSettings)
  const [showQueue, setShowQueue] = useState(false)
  const { data: queue } = useQuery({
    ...getStorageCleanupQueue,
    enabled: showQueue,
  })

  const { mutateAsync: updateSetting } = useSystemSettingsUpdate()

  const lastRun = systemSetting.storageCleanupLastRun

  const defaultValues: StorageCleanupFormValues = {
    enabled: systemSetting.storageCleanupEnabled,
    thresholdValue: `${systemSetting.storageCleanupThresholdValue}`,
    thresholdUnit: systemSetting.storageCleanupThresholdUnit,
    minScore: `${systemSetting.storageCleanupMinScore}`,
  }
  const lastSaved = useRef(JSON.stringify(defaultValues))

  const form = useForm({
    defaultValues,
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 1000,
      onChange: ({ formApi }) => {
        // Csak a felhasználó által módosított értéket mentsük, a mountkori
        // validáció ne írjon vissza a szerverre.
        const key = JSON.stringify(formApi.state.values)
        if (key === lastSaved.current || !formApi.state.isValid) {
          return
        }

        lastSaved.current = key
        formApi.handleSubmit()
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateSetting({
          storageCleanupEnabled: value.enabled,
          storageCleanupThresholdValue: Number(value.thresholdValue),
          storageCleanupThresholdUnit: value.thresholdUnit,
          storageCleanupMinScore: Number(value.minScore),
        })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const enabled = useStore(form.store, (state) => state.values.enabled)

  return (
    <div className="grid gap-6">
      <form.Field name="enabled">
        {(field) => (
          <div className="grid gap-1">
            <Label htmlFor={field.name} className="flex items-start gap-3">
              <p className="flex-1 text-sm leading-none font-medium">
                Tárhely alapú törlés
              </p>
              <Switch
                id={field.name}
                checked={field.state.value}
                onCheckedChange={field.handleChange}
              />
            </Label>
            <p className="text-muted-foreground text-sm">
              Ha a letöltések mappáját tartalmazó lemez szabad helye a küszöb
              alá csökken, pontszám szerint töröl.
            </p>
          </div>
        )}
      </form.Field>

      {enabled && (
        <>
          <div className="grid items-end gap-3 sm:grid-cols-2">
            <form.Field name="thresholdValue">
              {(field) => (
                <Field>
                  <div className="flex items-center gap-1.5">
                    <Label htmlFor={field.name}>Küszöb</Label>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          aria-label="Küszöb magyarázata"
                          className="text-muted-foreground hover:text-foreground -m-1 cursor-help rounded p-1"
                        >
                          <InfoIcon className="size-3.5" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-64">
                        A küszöb a letöltések mappáját tartalmazó lemez szabad
                        helyéhez viszonyul (a % a lemez teljes méretéből
                        számol). Ha a szabad hely ez alá esik, a legmagasabb
                        pontszámú torrentektől kezdve töröl, amíg a hely újra a
                        küszöb fölé nem kerül. A minimális pontszám alatti
                        torrent megmarad.
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Input
                    id={field.name}
                    name={field.name}
                    inputMode="numeric"
                    value={field.state.value}
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                  />
                  {field.state.meta.isTouched && (
                    <FieldError errors={field.state.meta.errors} />
                  )}
                </Field>
              )}
            </form.Field>

            <form.Field name="thresholdUnit">
              {(field) => (
                <Field>
                  <Label htmlFor={field.name}>Mértékegység</Label>
                  <Select
                    value={field.state.value}
                    onValueChange={(value) =>
                      field.handleChange(
                        value as StorageCleanupThresholdUnitEnum,
                      )
                    }
                  >
                    <SelectTrigger id={field.name} className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percent">Százalék (%)</SelectItem>
                      <SelectItem value="gb">Gigabájt (GB)</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </form.Field>

            <form.Field name="minScore">
              {(field) => (
                <Field>
                  <Label htmlFor={field.name}>Minimális pontszám</Label>
                  <InputGroup>
                    <InputGroupInput
                      id={field.name}
                      name={field.name}
                      inputMode="numeric"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                    />
                    <InputGroupAddon align="inline-end">
                      <InputGroupText>pont</InputGroupText>
                    </InputGroupAddon>
                  </InputGroup>
                  {field.state.meta.isTouched && (
                    <FieldError errors={field.state.meta.errors} />
                  )}
                </Field>
              )}
            </form.Field>
          </div>

          <Separator />

          <div className="grid gap-2">
            <p className="text-sm font-medium">Legutóbbi futás</p>
            {lastRun ? (
              <div className="grid gap-1 text-sm">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary">
                    {TRIGGER_LABELS[lastRun.trigger]}
                  </Badge>
                  <Badge variant="secondary">
                    {formatDateTime(new Date(lastRun.at * 1000).toISOString())}
                  </Badge>
                  <Badge variant="secondary">
                    {lastRun.deletedCount} törölve
                  </Badge>
                  <Badge
                    variant={
                      lastRun.thresholdReached ? 'secondary' : 'destructive'
                    }
                  >
                    {lastRun.thresholdReached
                      ? 'Küszöb elérve'
                      : 'Küszöb nem érhető el'}
                  </Badge>
                </div>
                <p className="text-muted-foreground">
                  Szabad hely — előtte, utána:{' '}
                  {formatFilesize(lastRun.freeBefore)} →{' '}
                  {formatFilesize(lastRun.freeAfter)}
                  {lastRun.freeAfter !== lastRun.freeBefore && (
                    <>
                      {' '}
                      (változás:{' '}
                      {lastRun.freeAfter > lastRun.freeBefore ? '+' : '−'}
                      {formatFilesize(
                        Math.abs(lastRun.freeAfter - lastRun.freeBefore),
                      )}
                      )
                    </>
                  )}
                </p>
                {lastRun.error && (
                  <p className="text-destructive break-all">{lastRun.error}</p>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                A takarítás még nem futott le.
              </p>
            )}
          </div>

          <Separator />

          <div className="grid gap-3">
            <div className="grid gap-1">
              <Label
                htmlFor="storage-cleanup-queue"
                className="flex items-start gap-3"
              >
                <p className="flex-1 text-sm leading-none font-medium">
                  Törlési sor megjelenítése
                </p>
                <Switch
                  id="storage-cleanup-queue"
                  checked={showQueue}
                  onCheckedChange={setShowQueue}
                />
              </Label>
              <p className="text-muted-foreground text-sm">
                Előnézet törlés nélkül: milyen sorrendben és miért törölnének a
                torrentek.
              </p>
            </div>

            {showQueue && queue && (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-muted-foreground text-sm">
                    Lemez: {formatFilesize(queue.totalBytes)} · Szabad:{' '}
                    {formatFilesize(queue.freeBytes)} · Küszöb:{' '}
                    {formatFilesize(queue.thresholdBytes)}
                  </p>
                  <Badge
                    variant={queue.belowThreshold ? 'destructive' : 'secondary'}
                  >
                    {queue.belowThreshold
                      ? 'a küszöb alatt'
                      : 'a küszöb felett'}
                  </Badge>
                </div>
                {!queue.hnrKnown && (
                  <p className="text-muted-foreground flex gap-2 text-sm">
                    <InfoIcon className="mt-0.5 size-4 shrink-0" />A Hit'n'Run
                    állapot ismeretlen az első futásig; ezek a torrentek nem
                    törlődnek.
                  </p>
                )}

                {queue.items.length > 0 ? (
                  <div className="grid max-h-80 gap-2 overflow-y-auto">
                    {queue.items.map((item) => (
                      <div
                        key={item.infoHash}
                        className="grid gap-1 rounded-md bg-muted/50 p-3"
                      >
                        <p className="line-clamp-2 text-sm break-all">
                          {item.name}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="secondary">{item.score} pont</Badge>
                          <Badge variant="secondary">
                            {formatFilesize(item.downloadedBytes)}
                          </Badge>
                          {item.protectedReason ? (
                            <Badge variant="outline">
                              {
                                STORAGE_CLEANUP_PROTECTED_REASON_LABELS[
                                  item.protectedReason
                                ]
                              }
                            </Badge>
                          ) : (
                            <Badge
                              variant={item.wouldDelete ? 'default' : 'outline'}
                            >
                              {item.wouldDelete
                                ? 'Törlésre jelölt'
                                : 'Pontszám a küszöb alatt'}
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm">
                    Nincs a relay munkamenetben olyan torrent, amit vizsgálni
                    lehetne.
                  </p>
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}
