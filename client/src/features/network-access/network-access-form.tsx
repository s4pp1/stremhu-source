import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Address4 } from 'ip-address'
import type { FormEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { useAppForm } from '@/shared/contexts/form-context'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getHealth, useBuildLocalUrl } from '@/shared/queries/app'
import { getSettings, useUpdateSetting } from '@/shared/queries/settings'

import { Separator } from '../../shared/components/ui/separator'
import { networkAccessDefaultValues } from './network-access.defaults'
import { NetworkSelector } from './network-selector'
import { UrlConfiguration } from './url-configuration'

export { networkAccessDefaultValues } from './network-access.defaults'

export const NETWORK_ACCESS_FORM_ID = 'network-access-form'
export const NETWORK_ACCESS_HEADER = {
  TITLE: 'Elérés beállítása',
  DESCRIPTION:
    'A Stremio csak biztonságos (HTTPS) kapcsolaton keresztül tud  addont telepíteni. Itt adhatod meg, milyen címen érje el a StremHU | Source-ot.',
}

const schema = z
  .object({
    connection: z.enum(['idle', 'pending', 'success', 'error']),
    enebledlocalIp: z.boolean(),
    address: z.string().trim(),
  })
  .superRefine(({ address, enebledlocalIp }, ctx) => {
    if (enebledlocalIp) {
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
        message: 'Érvénytelen HTTPS URL',
      })
      return
    }

    const parseUrl = new URL(parsedUrl.data)
    const lastCharacter = address.substring(address.length - 1)
    const noPath = parseUrl.pathname === '/' && lastCharacter !== '/'

    if (!noPath || parseUrl.search || parseUrl.hash) {
      ctx.addIssue({
        code: 'custom',
        path: ['address'],
        message: 'Nem tartalmazhat elérési utat, query-t vagy fragmentet',
      })
    }
  })

export type NetworkAccessProps = {
  onSuccess?: () => void
  onSkip?: () => void
  onValidated?: (isValid: boolean) => void
}

export function NetworkAccess(props: NetworkAccessProps) {
  const { onSuccess, onSkip, onValidated } = props

  const { data: setting } = useQuery(getSettings)
  assertExists(setting)

  const { confirm } = useConfirmDialog()

  const queryClient = useQueryClient()
  const { mutateAsync: updateSetting } = useUpdateSetting()
  const { mutateAsync: buildLocalUrl } = useBuildLocalUrl()

  const form = useAppForm({
    defaultValues: {
      ...networkAccessDefaultValues,
      enebledlocalIp: setting.enebledlocalIp,
      address: setting.address || '',
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onBlur: async ({ formApi }) => {
        const { isValid, values } = formApi.state

        if (!isValid) {
          if (onValidated) onValidated(false)
          return
        }

        const { enebledlocalIp, address } = values

        let appUrl = address

        if (enebledlocalIp) {
          const buildedUrl = await buildLocalUrl(appUrl)
          appUrl = buildedUrl.localUrl
        }

        try {
          if (onValidated) onValidated(false)
          formApi.setFieldValue('connection', 'pending')
          await updateSetting({ enebledlocalIp })
          await queryClient.fetchQuery(getHealth(appUrl))
          formApi.setFieldValue('connection', 'success')
          if (onValidated) onValidated(true)
        } catch (error) {
          formApi.setFieldValue('connection', 'error')
          if (onValidated) onValidated(false)
        }
      },
      onChange: async ({ formApi }) => {
        const { isValid, values } = formApi.state

        if (!isValid) {
          if (onValidated) onValidated(false)
          return
        }

        const { enebledlocalIp, address } = values

        let appUrl = address

        if (enebledlocalIp) {
          const buildedUrl = await buildLocalUrl(appUrl)
          appUrl = buildedUrl.localUrl
        }

        try {
          if (onValidated) onValidated(false)
          formApi.setFieldValue('connection', 'pending')
          await updateSetting({ enebledlocalIp })
          await queryClient.fetchQuery(getHealth(appUrl))
          formApi.setFieldValue('connection', 'success')
          if (onValidated) onValidated(true)
        } catch (error) {
          formApi.setFieldValue('connection', 'error')
          if (onValidated) onValidated(false)
        }
      },
      onChangeDebounceMs: 500,
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        const updatedSetting = await updateSetting(value)

        let appUrl = updatedSetting.address || '0.0.0.0'

        if (updatedSetting.enebledlocalIp) {
          const buildedUrl = await buildLocalUrl(appUrl)
          appUrl = buildedUrl.localUrl
        }

        await queryClient.fetchQuery(getHealth(appUrl))
        if (onSuccess) onSuccess()
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleSubmit: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  const handleSkip: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await confirm({
      title: 'Biztos kihagyod a beállítást?',
      description:
        'A lépés kihagyása után a "Beállítások" menüpont alatt tudod elvégezni a beállítást, addig az addon nem fog működni!',
      onConfirm: async () => {
        try {
          await updateSetting({
            address: '0.0.0.0',
            enebledlocalIp: true,
          })
          if (onSkip) onSkip()
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

  return (
    <form.AppForm>
      <form
        id={NETWORK_ACCESS_FORM_ID}
        className="grid gap-4"
        onSubmit={handleSubmit}
        onReset={handleSkip}
      >
        <NetworkSelector form={form} />
        <Separator />
        <UrlConfiguration form={form} />
      </form>
    </form.AppForm>
  )
}
