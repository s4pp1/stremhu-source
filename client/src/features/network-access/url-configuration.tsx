import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { LinkIcon, UnlinkIcon } from 'lucide-react'

import { Button } from '@/shared/components/ui/button'
import { Field, FieldError } from '@/shared/components/ui/field'
import { Input } from '@/shared/components/ui/input'
import { Spinner } from '@/shared/components/ui/spinner'
import { withForm } from '@/shared/contexts/form-context'
import { assertExists } from '@/shared/lib/utils'
import { getSettings } from '@/shared/queries/settings'

import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '../../shared/components/ui/item'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '../../shared/components/ui/tooltip'
import { networkAccessDefaultValues } from './network-access.defaults'

const addressMap = {
  ip: {
    label: 'Eszköz IPv4 címe',
    placeholder: 'Pl.: 192.168.1.100',
    description:
      'Annak az eszköznek a helyi IP címe, ahol a StremHU | Source fut.',
  },
  domain: {
    label: 'Domain cím',
    placeholder: 'Pl.: https://stremhu.yourdomain.com',
    description:
      'Olyan domain, amely a StremHU | Source-ot futtató eszközre irányít, és HTTPS-en keresztül érhető el.',
  },
}

const networkCheckMap = {
  pending: {
    icon: <Spinner />,
    title: 'Elérés ellenőrzése...',
  },
  success: {
    icon: <LinkIcon />,
    title: 'Sikeres kapcsolat!',
  },
  error: {
    icon: <UnlinkIcon />,
    title: 'Nem érhető el ezen a címen.',
  },
}

export const UrlConfiguration = withForm({
  defaultValues: networkAccessDefaultValues,
  render: ({ form }) => {
    const { data: setting } = useQuery(getSettings)
    assertExists(setting)

    const networkConfig = form.store.state.values.enebledlocalIp
      ? 'ip'
      : 'domain'

    return (
      <div className="grid gap-2">
        <Item className="p-0">
          <ItemContent>
            <ItemTitle>{addressMap[networkConfig].label}</ItemTitle>
            <ItemDescription>
              {addressMap[networkConfig].description}
            </ItemDescription>
          </ItemContent>
          <form.Subscribe selector={(state) => [state.values.connection]}>
            {([connection]) =>
              connection !== 'idle' && (
                <ItemActions>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant={
                          connection === 'error' ? 'destructive' : 'default'
                        }
                        size="icon-sm"
                        className={clsx([
                          'rounded-full',
                          connection === 'success' && 'bg-green-500 text-white',
                        ])}
                      >
                        {networkCheckMap[connection].icon}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{networkCheckMap[connection].title}</p>
                    </TooltipContent>
                  </Tooltip>
                </ItemActions>
              )
            }
          </form.Subscribe>
        </Item>
        <form.Field name="address">
          {(field) => (
            <Field>
              <Input
                name={field.name}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => {
                  field.handleChange(e.target.value)
                }}
                placeholder={addressMap[networkConfig].placeholder}
              />
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
      </div>
    )
  },
})
