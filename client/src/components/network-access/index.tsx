import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import * as z from 'zod'

import { parseApiError } from '@/common/utils'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { getSettings, useUpdateSetting } from '@/queries/settings'

import { Separator } from '../ui/separator'
import { UrlConfiguration } from './url-configuration'

const accessOptions = [
  {
    label: 'Hozzáférés otthoni hálózaton',
    description: (
      <>
        Csak a helyi hálózaton használod. A Stremio egy biztonságos HTTPS címet
        generál a helyi IP-dhez a{' '}
        <a
          className="underline italic "
          href="https://local-ip.medicmobile.org/"
          target="_blank"
        >
          https://local-ip.medicmobile.org/
        </a>{' '}
        segítségével.
      </>
    ),
    value: 'true',
  },
  {
    label: 'Távoli elérés saját domainnel',
    description: (
      <>
        Használd ezt, ha az internetről is el szeretnéd érni a StremHU |
        Source-ot. Adj meg egy olyan domaint (pl. DDNS-szolgáltatóval, mint a{' '}
        <a
          className="underline italic "
          href="https://noip.com/"
          target="_blank"
        >
          https://noip.com
        </a>
        ), amely a StremHU | Source-ot futtató eszközre mutat, és biztosítja a
        HTTPS-kapcsolatot.
      </>
    ),
    value: 'false',
  },
]

const schema = z.object({
  enebledlocalIp: z.boolean(),
})

export function NetworkAccess() {
  const { data: setting } = useQuery(getSettings)
  if (!setting) throw new Error(`Nincs "settings" a cache-ben`)

  const { mutateAsync: updateSetting } = useUpdateSetting()

  const form = useForm({
    defaultValues: {
      enebledlocalIp: setting.enebledlocalIp,
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 1000,
      onChange: ({ formApi }) => {
        const { isValid } = formApi.store.state

        if (isValid) {
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
        <CardTitle>Elérés beállítása</CardTitle>
        <CardDescription>
          A Stremio csak biztonságos (HTTPS) kapcsolaton keresztül tud addont
          telepíteni. Itt adhatod meg, milyen címen érje el a StremHU |
          Source-ot.
        </CardDescription>
      </CardHeader>
      <form name="setting">
        <CardContent className="grid gap-4">
          <form.Field name="enebledlocalIp">
            {(field) => (
              <RadioGroup
                value={field.state.value.toString()}
                onValueChange={(value) => {
                  const booleanValue = value === 'true'
                  field.handleChange(booleanValue)
                }}
              >
                {accessOptions.map((accessOption) => (
                  <div
                    key={accessOption.value}
                    className="flex items-start gap-3"
                  >
                    <RadioGroupItem
                      value={accessOption.value}
                      id={accessOption.value}
                    />
                    <div className="grid gap-2">
                      <Label htmlFor={accessOption.value}>
                        {accessOption.label}
                      </Label>
                      <p className="text-muted-foreground text-sm">
                        {accessOption.description}
                      </p>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            )}
          </form.Field>
          <Separator />
        </CardContent>
      </form>
      <UrlConfiguration />
    </Card>
  )
}
