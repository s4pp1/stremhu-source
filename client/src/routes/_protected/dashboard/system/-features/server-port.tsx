import { useForm } from '@tanstack/react-form'
import { useSuspenseQueries } from '@tanstack/react-query'
import { LockIcon, ServerIcon } from 'lucide-react'
import { toast } from 'sonner'
import * as z from 'zod'

import { Badge } from '@/shared/components/ui/badge'
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
} from '@/shared/components/ui/input-group'
import {
  Item,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { parseApiError } from '@/shared/lib/utils'
import {
  getSystemSettings,
  getSystemStatus,
  useSystemSettingsUpdate,
} from '@/shared/queries/system'

const schema = z.object({
  port: z.coerce
    .number<string>({ message: 'Csak szám adható meg.' })
    .int('A port csak egész szám lehet.')
    .min(1, 'A port minimális értéke 1.')
    .max(65535, 'A port maximális értéke 65535.'),
})

export function ServerPort() {
  const [{ data: systemSettings }, { data: systemStatus }] = useSuspenseQueries(
    {
      queries: [getSystemSettings, getSystemStatus],
    },
  )

  const { mutateAsync: updateSetting } = useSystemSettingsUpdate()

  const isLocked = systemStatus.isPortOverridden || systemStatus.isDocker

  const form = useForm({
    defaultValues: {
      port: systemSettings.port.toString(),
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 1000,
      onChange: ({ formApi }) => {
        if (!isLocked && formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateSetting({
          port: Number(value.port),
        })
        toast.success(
          'A szerver portja elmentve! Az új beállítás életbe lépéséhez indítsd újra a szervert.',
        )
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
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2">
            <ServerIcon className="size-5 text-primary" />
            Szerver port
          </CardTitle>
          {isLocked && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <LockIcon className="size-3" />
              Zárolva
            </Badge>
          )}
        </div>
        <CardDescription>
          A webszerver és API által használt hálózati port beállítása.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <Item variant="muted">
          <ItemContent>
            <ItemTitle>Kiszolgáló portja</ItemTitle>
            <ItemDescription>
              {isLocked
                ? 'A port környezeti változóban (PORT) vagy a Docker konfigurációban van megadva, így a felületen nem módosítható.'
                : 'A port módosítása után a változtatások érvénybe léptetéséhez indítsd újra a szervert!'}
            </ItemDescription>
          </ItemContent>
        </Item>

        <form.Field name="port">
          {(field) => {
            const hasError = !field.state.meta.isValid
            return (
              <Field data-invalid={hasError}>
                <InputGroup>
                  <InputGroupInput
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={65535}
                    id={field.name}
                    name={field.name}
                    value={field.state.value}
                    disabled={isLocked}
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    placeholder="7070"
                  />
                  {isLocked && (
                    <InputGroupAddon align="inline-end">
                      <LockIcon className="size-4 text-muted-foreground" />
                    </InputGroupAddon>
                  )}
                </InputGroup>
                <FieldError errors={field.state.meta.errors} />
              </Field>
            )
          }}
        </form.Field>
      </CardContent>
    </Card>
  )
}
