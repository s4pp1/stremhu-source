import { useForm } from '@tanstack/react-form'
import { useSuspenseQuery } from '@tanstack/react-query'
import { BrushCleaningIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
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
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Label } from '@/shared/components/ui/label'
import { Separator } from '@/shared/components/ui/separator'
import { Switch } from '@/shared/components/ui/switch'
import { parseApiError } from '@/shared/lib/utils'
import {
  getSystemSettings,
  useSystemIndexersCleanup,
  useSystemSettingsUpdate,
} from '@/shared/queries/system'

const schema = z.object({
  hitAndRun: z.boolean(),
  keepSeed: z.coerce
    .number<string>('Csak szám adható meg')
    .positive('Csak pozitív szám adható meg.')
    .nullable(),
})

export function KeepSeeding() {
  const { data: systemSetting } = useSuspenseQuery(getSystemSettings)

  const confirmDialog = useConfirmDialog()

  const { mutateAsync: updateSetting } = useSystemSettingsUpdate()
  const { mutateAsync: cleanupIndexers } = useSystemIndexersCleanup()

  const keepSeedDays = useMemo(() => {
    if (systemSetting.keepSeedSeconds > 0) {
      const days = systemSetting.keepSeedSeconds / (24 * 60 * 60)
      return `${days}`
    }

    return null
  }, [systemSetting.keepSeedSeconds])

  const form = useForm({
    defaultValues: {
      hitAndRun: systemSetting.hitAndRun,
      keepSeed: keepSeedDays,
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
        let keepSeedSeconds = 0

        if (value.keepSeed) {
          const days = Number(value.keepSeed)
          keepSeedSeconds = days * 24 * 60 * 60
        }

        await updateSetting({
          keepSeedSeconds,
          hitAndRun: value.hitAndRun,
        })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleCleanup: MouseEventHandler<HTMLButtonElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()

    await confirmDialog.confirm({
      title: 'Biztos letuttatod a manuális ellenőrzést?',
      description:
        'A futtatás ellenére a hajnalban időzített futtatás is le fog futni.',
      onConfirm: async () => {
        try {
          await cleanupIndexers()
          toast.success('A manuális ellenőrzés sikeresen lefutott.')
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Automatikus torrent törlés</CardTitle>
        <CardDescription>
          Minden nap hajnalban lefut az ellenőrzés, de torrent csak akkor kerül
          törlésre, ha a beállított feltételek mindegyike teljesül.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <form.Field name="hitAndRun">
          {(field) => (
            <div className="grid gap-1">
              <Label htmlFor={field.name} className="flex items-start gap-3">
                <p className="flex-1 text-sm leading-none font-medium">
                  Hit'n'Run alapú törlés
                </p>
                <Switch
                  id={field.name}
                  checked={field.state.value}
                  onCheckedChange={field.handleChange}
                />
              </Label>
              <p className="text-muted-foreground text-sm">
                Ellenőrzi a tracker oldal alapján a teljesítést és csak ezt
                követően törlődhet.
              </p>
            </div>
          )}
        </form.Field>
        <div className="grid gap-3">
          <form.Field name="keepSeed">
            {(field) => (
              <div className="grid gap-3">
                <div className="grid gap-1">
                  <Label
                    htmlFor={field.name}
                    className="flex items-start gap-3"
                  >
                    <p className="flex-1 text-sm leading-none font-medium">
                      Lejátszás alapú törlés
                    </p>
                    <Switch
                      id={field.name}
                      checked={field.state.value !== null}
                      onCheckedChange={(checked) => {
                        field.setValue(checked ? '4' : null)
                      }}
                    />
                  </Label>
                  <p className="text-muted-foreground text-sm">
                    A torrent csak akkor törlődhet, ha a legutóbbi lejátszás óta
                    eltelt a beállított idő.
                  </p>
                </div>
                {field.state.value !== null && (
                  <Field>
                    <InputGroup>
                      <InputGroupInput
                        placeholder="Hány nap után engedje?"
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
                        <InputGroupText>nap után</InputGroupText>
                      </InputGroupAddon>
                    </InputGroup>
                    {field.state.meta.isTouched && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )}
              </div>
            )}
          </form.Field>
        </div>
        <Separator />
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Torrentek ellenőrzése</ItemTitle>
            <ItemDescription>
              Torrentek ellenőrzésének indítása!
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="destructive"
              className="rounded-full"
              onClick={handleCleanup}
            >
              <BrushCleaningIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
