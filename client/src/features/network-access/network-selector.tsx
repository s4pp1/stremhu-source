import { useStore } from '@tanstack/react-form'
import { useSuspenseQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { Button } from '@/shared/components/ui/button'
import { withForm } from '@/shared/contexts/form-context'
import { getNetworkProviders } from '@/shared/queries/network'

import { NetworkCard } from './components/network-card'
import { networkAccessDefaultValues } from './network-access.defaults'
import type { NetworkAccessFormValues } from './network-access.schema'

type Option = {
  mode: NetworkAccessFormValues['mode']
  name: string
  description: string
  providerId?: string
}

export const NetworkSelector = withForm({
  defaultValues: networkAccessDefaultValues,
  render: ({ form }) => {
    const { data: providers } = useSuspenseQuery(getNetworkProviders)

    const formValues = useStore(form.store, (state) => state.values)

    const handleSelect = (option: Option) => {
      const { mode, providerId } = option

      form.baseStore.setState((state) => {
        if (providerId) {
          return {
            ...state,
            values: {
              mode: 'auto',
              provider: providerId,
              email: '',
              host: '',
              token: '',
              connection: 'public',
            },
          }
        }

        if (mode === 'local') {
          return {
            ...state,
            values: {
              mode: 'local',
            },
          }
        }

        if (mode === 'manual') {
          return {
            ...state,
            values: {
              mode: 'manual',
              host: '',
            },
          }
        }

        return state
      })
    }

    const handleReset = () => {
      form.baseStore.setState((state) => ({
        ...state,
        values: {
          mode: 'none',
        },
      }))
    }

    const options: Option[] = useMemo(() => {
      const selectableProviders: Option[] = providers.map((provider) => {
        return {
          mode: 'auto',
          providerId: provider.id,
          name: provider.name,
          description: provider.name,
        }
      })

      return [
        {
          mode: 'local',
          name: 'Otthoni konfiguráció',
          description: 'A szerver csak a helyi hálózatban érhető el.',
        },
        ...selectableProviders,
        {
          mode: 'manual',
          name: 'Reverse Proxy',
          description: 'Saját domain használata, reverse proxy segítségével.',
        },
      ]
    }, [providers])

    const selectedOption = useMemo(() => {
      if (formValues.mode === 'none') {
        return null
      }

      if (formValues.mode === 'auto') {
        return options.find(
          (option) => option.providerId === formValues.provider,
        )
      }

      return options.find((option) => option.mode === formValues.mode)
    }, [options, formValues.mode])

    return (
      <div className="grid gap-4">
        {selectedOption ? (
          <NetworkCard
            name={selectedOption.name}
            description={selectedOption.description}
            isSelected
            onSelect={() => {}}
          />
        ) : (
          options.map((option) => {
            return (
              <NetworkCard
                key={`${option.mode}-${option.providerId}`}
                name={option.name}
                description={option.description}
                onSelect={() => handleSelect(option)}
              />
            )
          })
        )}

        {formValues.mode !== 'none' && (
          <div className="flex justify-end">
            <Button
              type="button"
              variant="link"
              size="sm"
              className="p-0 text-xs underline-offset-4 h-auto hover:underline"
              onClick={handleReset}
            >
              Konfiguráció módosítása
            </Button>
          </div>
        )}
      </div>
    )
  },
})
