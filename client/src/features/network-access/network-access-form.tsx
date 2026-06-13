import { useSuspenseQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import { getNetworkSettings, useNetworkConfig } from '@/shared/queries/network'

import type { NetworkAccessFormValues } from './network-access.schema'
import { networkAccessSchema } from './network-access.schema'

export const NETWORK_ACCESS_FORM_ID = 'network-access-form'
export const NETWORK_ACCESS_HEADER = {
  TITLE: 'Elérés beállítása',
  DESCRIPTION:
    'A kliensek elvárják a biztonságos domain alapú SSL tanúsítvánnyal rendelkező elérést.',
}

export function useNetworkAccessForm() {
  const { data: networkSettings } = useSuspenseQuery(getNetworkSettings)
  const { mutateAsync: configNetwork } = useNetworkConfig()

  const defaultValues = useMemo((): NetworkAccessFormValues => {
    if (networkSettings.mode === 'local') {
      return {
        mode: 'local',
      }
    }

    return networkSettings
  }, [networkSettings])

  const form = useAppForm({
    defaultValues,
    validators: {
      onChange: networkAccessSchema,
    },

    onSubmit: async ({ value }) => {
      try {
        if (value.mode === 'none') {
          return
        }

        const networkSetup = await configNetwork(value)

        toast.success(
          <div className="flex flex-col gap-1">
            <p>Hálózati beállítások sikeresen elmentve! A szerver újraindul.</p>
            <p>
              Az új elérhetőség:{' '}
              <a
                href={networkSetup.appUrl}
                target="_blank"
                rel="noreferrer"
                className="underline font-bold"
              >
                {networkSetup.appUrl}
              </a>
            </p>
          </div>,
          {
            duration: Infinity,
          },
        )
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return form
}
