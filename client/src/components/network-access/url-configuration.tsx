import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Address4 } from 'ip-address'
import { CheckIcon, XIcon } from 'lucide-react'
import type { FormEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { parseApiError } from '@/common/utils'
import { Alert, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { CardContent, CardFooter } from '@/components/ui/card'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { useCheckAddress } from '@/queries/app'
import { getSettings, useUpdateSetting } from '@/queries/settings'

import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '../ui/item'

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
    title: 'Konfiguráció ellenőrzése',
  },
  success: {
    icon: <CheckIcon />,
    title: 'Sikeres konfiguráció!',
  },
  error: {
    icon: <XIcon />,
    title: 'A megadott elérési út nem megfelelő!',
  },
}

export function UrlConfiguration() {
  const navigate = useNavigate({
    from: '/setup/address',
  })

  const { data: setting } = useQuery(getSettings)
  if (!setting) throw new Error(`Nincs "settings" a cache-ben`)

  const networkConfig = setting.enebledlocalIp ? 'ip' : 'domain'

  const schema = z
    .object({
      address: z.string(),
    })
    .superRefine(({ address }, ctx) => {
      if (setting.enebledlocalIp) {
        try {
          new Address4(address)
          if (address.includes('/') || address.includes(':')) {
            throw new Error()
          }
        } catch (error) {
          ctx.addIssue({
            code: 'custom',
            path: ['address'],
            message: 'Csak IPv4 cím adható meg (protokoll/subnet/port nélkül)',
          })
        }

        return
      }

      const httpsUrl = z.url({
        protocol: /^https$/,
        error: 'Csak HTTPS engedélyezett',
      })

      const parsedUrl = httpsUrl.safeParse(address)

      if (!parsedUrl.success) {
        ctx.addIssue({
          code: 'custom',
          path: ['address'],
          message: parsedUrl.error.message || 'Érvénytelen HTTPS URL',
        })
        return
      }

      const parseUrl = new URL(parsedUrl.data)
      const lastCharacter = address.substring(address.length - 1)
      const noPath = parseUrl.pathname === '/' && lastCharacter !== '/'

      if (!noPath || parseUrl.search || parseUrl.hash) {
        ctx.addIssue({
          code: 'custom',
          message: 'Nem tartalmazhat elérési utat, query-t vagy fragmentet',
        })
      }
    })

  const { mutateAsync: updateSetting } = useUpdateSetting()
  const { mutateAsync: checkAddress, status: checkAddressStatus } =
    useCheckAddress()

  const form = useForm({
    defaultValues: {
      address: setting.address,
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 2000,
      onChange: async ({ formApi }) => {
        const { isValid, values } = formApi.store.state

        if (isValid) {
          try {
            await checkAddress({
              ...values,
              enebledlocalIp: setting.enebledlocalIp,
            })
          } catch {}
        } else {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateSetting(value)
        navigate({ to: '/settings' })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const onSubmit: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  return (
    <form className="grid gap-4" onSubmit={onSubmit}>
      <CardContent className="grid gap-2">
        <Item className="p-0">
          <ItemContent>
            <ItemTitle>{addressMap[networkConfig].label}</ItemTitle>
            <ItemDescription>
              {addressMap[networkConfig].description}
            </ItemDescription>
          </ItemContent>

          <ItemActions>
            <Button variant="outline" size="sm">
              Action
            </Button>
          </ItemActions>
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

        {checkAddressStatus !== 'idle' && (
          <Alert
            variant={checkAddressStatus === 'error' ? 'destructive' : 'default'}
          >
            {networkCheckMap[checkAddressStatus].icon}
            <AlertTitle>{networkCheckMap[checkAddressStatus].title}</AlertTitle>
          </Alert>
        )}
      </CardContent>
      <CardFooter className="flex gap-2 justify-end">
        <Button variant="link">Kihagyás</Button>
        <Button type="submit">Mentés</Button>
      </CardFooter>
    </form>
  )
}
