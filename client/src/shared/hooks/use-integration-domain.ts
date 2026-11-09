import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { assertExists } from '../lib/utils'
import { getSystemStatus } from '../queries/system'

type UseIntegrationDomainProps = {
  apiKey: string
}

export function useIntegrationDomain(props: UseIntegrationDomainProps) {
  const { apiKey } = props

  const { data: systemStatus } = useQuery(getSystemStatus)
  assertExists(systemStatus)

  const stremio = useMemo(() => {
    const endpointHost = new URL(systemStatus.appUrl).host
    const endpoint = `${endpointHost}/api/${apiKey}/stremio/manifest.json`

    const appEndpoint = `stremio://${endpoint}`
    const urlEndpoint = `https://${endpoint}`
    const webEndpoint = `https://web.stremio.com/#/addons?addon=${urlEndpoint}`

    return {
      appEndpoint,
      webEndpoint,
      urlEndpoint,
    }
  }, [systemStatus.appUrl, apiKey])

  return {
    stremio,
    nuvioUrl: `${systemStatus.appUrl}/api/${apiKey}/stremio/manifest.json`,
    torznabUrl: `${systemStatus.appUrl}/api/torznab`,
  }
}
