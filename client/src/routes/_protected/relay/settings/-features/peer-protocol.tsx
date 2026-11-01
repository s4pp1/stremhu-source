import { useForm } from '@tanstack/react-form'
import { useSuspenseQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import * as z from 'zod'

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
import { Label } from '@/shared/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Switch } from '@/shared/components/ui/switch'
import { RelayEncryptionEnum } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { getRelaySettings, useUpdateRelaySetting } from '@/shared/queries/relay'

const encryptionOptions: { value: RelayEncryptionEnum; label: string }[] = [
  { value: RelayEncryptionEnum.enabled, label: 'Engedélyezett' },
  { value: RelayEncryptionEnum.forced, label: 'Kötelező' },
  { value: RelayEncryptionEnum.disabled, label: 'Kikapcsolva' },
]

const schema = z.object({
  encryption: z.enum(RelayEncryptionEnum),
  enableUtp: z.boolean(),
})

export function PeerProtocol() {
  const { data: relaySettings } = useSuspenseQuery(getRelaySettings)

  const { mutateAsync: updateSetting } = useUpdateRelaySetting()

  const form = useForm({
    defaultValues: {
      encryption: relaySettings.encryption,
      enableUtp: relaySettings.enableUtp,
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateSetting(value)
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
        <CardTitle>Peer kapcsolatok</CardTitle>
        <CardDescription>
          A változtatás az új kapcsolatokra vonatkozik.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-6">
        <form.Field name="encryption">
          {(field) => (
            <Field>
              <FieldLabel htmlFor={field.name}>
                Protokoll-titkosítás (MSE/PE)
              </FieldLabel>
              <Select
                value={field.state.value}
                name={field.name}
                onValueChange={(value) =>
                  field.handleChange(value as RelayEncryptionEnum)
                }
              >
                <SelectTrigger id={field.name} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {encryptionOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FieldDescription>
                Kötelező titkosításnál csak titkosított peer kapcsolat jön
                létre, így a forgalomból nem olvasható ki, melyik torrentről van
                szó. Néhány titkosítást nem támogató peer kieshet.
              </FieldDescription>
            </Field>
          )}
        </form.Field>
        <form.Field name="enableUtp">
          {(field) => (
            <Field>
              <div className="flex items-center space-x-2">
                <Switch
                  id={field.name}
                  checked={field.state.value}
                  onCheckedChange={field.handleChange}
                />
                <Label htmlFor={field.name}>
                  uTP (UDP) kapcsolatok engedélyezése
                </Label>
              </div>
              <FieldDescription>
                Kikapcsolva csak TCP kapcsolatok jönnek létre. Egyes routereken
                a sok uTP kapcsolat megnövelheti a hálózat késleltetését.
              </FieldDescription>
            </Field>
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
