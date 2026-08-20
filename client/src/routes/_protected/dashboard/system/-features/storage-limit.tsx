import { useForm } from '@tanstack/react-form'
import { useSuspenseQuery } from '@tanstack/react-query'
import { InfoIcon } from 'lucide-react'
import { useMemo } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/shared/components/ui/alert'
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
import { Switch } from '@/shared/components/ui/switch'
import { parseApiError } from '@/shared/lib/utils'
import {
  getSystemSettings,
  useSystemSettingsUpdate,
} from '@/shared/queries/system'

const BYTES_IN_GIGABYTE = 1024 * 1024 * 1024

const DEFAULT_MAX_STORAGE_GB = '100'

const schema = z.object({
  maxStorage: z.coerce
    .number<string>('Csak szám adható meg')
    .positive('Csak pozitív szám adható meg.')
    .nullable(),
})

export function StorageLimit() {
  const { data: systemSettings } = useSuspenseQuery(getSystemSettings)

  const { mutateAsync: updateSetting } = useSystemSettingsUpdate()

  const maxStorageGigabytes = useMemo(() => {
    if (systemSettings.maxStorageBytes > 0) {
      const gigabytes = systemSettings.maxStorageBytes / BYTES_IN_GIGABYTE
      return `${gigabytes}`
    }

    return null
  }, [systemSettings.maxStorageBytes])

  const form = useForm({
    defaultValues: {
      maxStorage: maxStorageGigabytes,
    },
    validators: {
      onChange: schema,
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
        let maxStorageBytes = 0

        if (value.maxStorage) {
          const gigabytes = Number(value.maxStorage)
          maxStorageBytes = gigabytes * BYTES_IN_GIGABYTE
        }

        await updateSetting({
          maxStorageBytes,
        })
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
        <CardTitle>Tárhely korlát</CardTitle>
        <CardDescription>
          A letöltések nem foglalhatnak több helyet a megadottnál. Túllépéskor a
          legrégebben nézett torrentek automatikusan törlődnek.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <form.Field name="maxStorage">
          {(field) => (
            <div className="grid gap-3">
              <div className="grid gap-1">
                <Label htmlFor={field.name} className="flex items-start gap-3">
                  <p className="flex-1 text-sm leading-none font-medium">
                    Tárhely korlát figyelése
                  </p>
                  <Switch
                    id={field.name}
                    checked={field.state.value !== null}
                    onCheckedChange={(checked) => {
                      field.setValue(checked ? DEFAULT_MAX_STORAGE_GB : null)
                    }}
                  />
                </Label>
                <p className="text-muted-foreground text-sm">
                  Az ellenőrzés negyedóránként fut. A seedben tartásra jelölt,
                  az éppen streamelt és a hit and run időn belüli torrentek nem
                  kerülnek törlésre.
                </p>
              </div>
              {field.state.value !== null && (
                <>
                  <Field>
                    <InputGroup>
                      <InputGroupInput
                        placeholder="Mennyi helyet foglalhatnak?"
                        inputMode="numeric"
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => {
                          field.handleChange(e.target.value)
                        }}
                      />
                      <InputGroupAddon align="inline-end">
                        <InputGroupText>GB</InputGroupText>
                      </InputGroupAddon>
                    </InputGroup>
                    {field.state.meta.isTouched && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                  {systemSettings.hitAndRun && (
                    <Alert>
                      <InfoIcon />
                      <AlertTitle>
                        A Hit&apos;n&apos;Run korlátozhatja a takarítást
                      </AlertTitle>
                      <AlertDescription>
                        Az „Automatikus torrent törlés” kártyán a
                        Hit&apos;n&apos;Run be van kapcsolva, így a még nem
                        teljesített torrentek a korlát ellenére sem törlődnek.
                        Emiatt előfordulhat, hogy a beállított méret túllépésre kerül.
                      </AlertDescription>
                    </Alert>
                  )}
                </>
              )}
            </div>
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
