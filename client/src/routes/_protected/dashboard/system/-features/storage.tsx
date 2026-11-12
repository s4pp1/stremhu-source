import { useQuery, useSuspenseQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Field, FieldError } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from '@/shared/components/ui/input-group'
import { Label } from '@/shared/components/ui/label'
import { Progress } from '@/shared/components/ui/progress'
import { Switch } from '@/shared/components/ui/switch'
import { parseApiError } from '@/shared/lib/utils'
import {
  getSystemSettings,
  getSystemStorage,
  useSystemSettingsUpdate,
} from '@/shared/queries/system'
import { formatFilesize } from '@/shared/utils/file.util'

// A felületen GB-ban adjuk meg (1 GB = 1024³ bájt, a kijelzéssel egyezően)
const GB = 1024 * 1024 * 1024

const schema = z.object({
  storageLimit: z.coerce
    .number<string>('Csak szám adható meg')
    .positive('Csak pozitív szám adható meg.'),
})

export function StorageSettings() {
  const { data: systemSettings } = useSuspenseQuery(getSystemSettings)
  const { data: storage } = useQuery(getSystemStorage)

  const { mutateAsync: updateSetting } = useSystemSettingsUpdate()

  const savedLimitGb = systemSettings.storageLimitBytes
    ? `${Number((systemSettings.storageLimitBytes / GB).toFixed(2))}`
    : null

  const [isAuto, setIsAuto] = useState(savedLimitGb === null)
  const [limitGb, setLimitGb] = useState(savedLimitGb ?? '')

  // A beírt érték ellenőrzése (a magyar tizedesvesszőt is elfogadja)
  const parsed = useMemo(() => {
    const value = limitGb.trim().replace(',', '.')
    if (!value) {
      return { bytes: null, error: null }
    }

    const result = schema.shape.storageLimit.safeParse(value)
    if (!result.success) {
      return {
        bytes: null,
        error: result.error.issues[0]?.message ?? 'Hibás érték',
      }
    }

    return { bytes: Math.round(result.data * GB), error: null }
  }, [limitGb])

  // Automatikus mentés 1 mp-cel a gépelés után, mint az admin többi mezőjénél
  useEffect(() => {
    if (isAuto || parsed.bytes === null) return
    if (parsed.bytes === systemSettings.storageLimitBytes) return

    const storageLimitBytes = parsed.bytes
    const timeout = setTimeout(() => {
      updateSetting({ storageLimitBytes }).catch((err: unknown) => {
        toast.error(parseApiError(err))
      })
    }, 1000)

    return () => clearTimeout(timeout)
  }, [isAuto, parsed.bytes, systemSettings.storageLimitBytes, updateSetting])

  const handleAutoChange = async (checked: boolean) => {
    setIsAuto(checked)

    if (checked) {
      setLimitGb('')
      if (systemSettings.storageLimitBytes !== null) {
        try {
          await updateSetting({ storageLimitBytes: null })
        } catch (err) {
          toast.error(parseApiError(err))
        }
      }
    }
  }

  const placeholder = storage
    ? `pl. ${Math.max(1, Math.floor(storage.capacityBytes / GB))}`
    : 'pl. 1024'

  const usedPercent = storage?.capacityBytes
    ? Math.min(100, (storage.usedBytes / storage.capacityBytes) * 100)
    : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tárhely</CardTitle>
        <CardDescription>
          A letöltésekre használható hely. Alapból a lemez szabad helye alapján
          automatikusan számol, de kézzel is megadhatod.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        {storage && (
          <div className="grid gap-2">
            <Progress value={usedPercent} />
            <div className="text-muted-foreground flex flex-wrap justify-between gap-2 text-sm">
              <span>
                {formatFilesize(storage.usedBytes)} /{' '}
                {formatFilesize(storage.capacityBytes)} foglalt
                {storage.mode === 'manual'
                  ? ' (kézi korlát)'
                  : ' (automatikus)'}
              </span>
              <span>Szabad: {formatFilesize(storage.freeBytes)}</span>
            </div>
            <div className="text-muted-foreground text-sm">
              Lemez: {formatFilesize(storage.diskTotalBytes)} (szabad:{' '}
              {formatFilesize(storage.diskFreeBytes)})
            </div>
            {storage.evictableCount > 0 && (
              <p className="text-muted-foreground text-sm">
                {storage.evictableCount} torrent (
                {formatFilesize(storage.evictableBytes)}) seedel, és szükség
                esetén törölhető.
              </p>
            )}
          </div>
        )}
        <div className="grid gap-3">
          <div className="grid gap-1">
            <Label htmlFor="storageAuto" className="flex items-start gap-3">
              <p className="flex-1 text-sm leading-none font-medium">
                Automatikus felismerés
              </p>
              <Switch
                id="storageAuto"
                checked={isAuto}
                onCheckedChange={handleAutoChange}
              />
            </Label>
            <p className="text-muted-foreground text-sm">
              {isAuto
                ? 'A lemez szabad helye alapján számol.'
                : 'A torrentek összesen legfeljebb ennyi helyet foglalhatnak.'}
            </p>
          </div>
          {!isAuto && (
            <Field>
              <InputGroup>
                <InputGroupInput
                  placeholder={placeholder}
                  inputMode="decimal"
                  id="storageLimit"
                  name="storageLimit"
                  value={limitGb}
                  onChange={(e) => setLimitGb(e.target.value)}
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupText>GB</InputGroupText>
                </InputGroupAddon>
              </InputGroup>
              {parsed.error && (
                <FieldError errors={[{ message: parsed.error }]} />
              )}
              {systemSettings.storageLimitBytes === null && (
                <p className="text-muted-foreground text-sm">
                  Amíg nem adsz meg értéket, az automatikus felismerés marad
                  érvényben.
                </p>
              )}
            </Field>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
