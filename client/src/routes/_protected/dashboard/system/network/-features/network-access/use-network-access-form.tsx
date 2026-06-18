import { useSuspenseQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import {
  getNetworkProviders,
  getNetworkSettings,
  useNetworkConfig,
} from '@/shared/queries/network'

import type { NetworkAccessFormValues } from './network-access.schema'
import { createNetworkAccessSchema } from './network-access.schema'

type UseNetworkAccessFormProps = {
  onSuccess?: () => void
}

export function useNetworkAccessForm(props: UseNetworkAccessFormProps = {}) {
  const { onSuccess } = props

  const { data: networkSettings } = useSuspenseQuery(getNetworkSettings)
  const { data: providers } = useSuspenseQuery(getNetworkProviders)
  const { mutateAsync: configNetwork } = useNetworkConfig()

  const defaultValues = useMemo((): NetworkAccessFormValues => {
    if (networkSettings.mode === 'local') {
      return {
        mode: 'local',
      }
    }

    return networkSettings
  }, [networkSettings])

  const schema = useMemo(
    () => createNetworkAccessSchema(providers),
    [providers],
  )

  const form = useAppForm({
    defaultValues,
    validators: {
      onChange: schema,
    },

    onSubmit: async ({ value }) => {
      try {
        if (value.mode === 'none') {
          return
        }

        const networkSetup = await configNetwork(value)

        toast.success(
          <div className="flex flex-col gap-1">
            <p>A szerver az új beállítások érvénybe léptetéséhez újraindul.</p>
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

        onSuccess?.()
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return form
}
