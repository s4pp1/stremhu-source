import { Label } from '@/shared/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/shared/components/ui/radio-group'
import { withForm } from '@/shared/contexts/form-context'

import { networkAccessDefaultValues } from './network-access.defaults'

const accessOptions = [
  {
    label: 'Hozzáférés otthoni hálózaton',
    description: (
      <>
        Csak a helyi hálózaton használod. A StremHU | Source egy biztonságos
        HTTPS címet generál a helyi IP-dhez a{' '}
        <a
          className="underline italic "
          href="https://local-ip.medicmobile.org"
          target="_blank"
        >
          https://local-ip.medicmobile.org
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

export const NetworkSelector = withForm({
  defaultValues: networkAccessDefaultValues,
  render: ({ form }) => {
    return (
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
              <div key={accessOption.value} className="flex items-start gap-3">
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
    )
  },
})
