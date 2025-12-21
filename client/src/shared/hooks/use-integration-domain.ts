import { useQuery } from '@tanstack/react-query'

import { getMetadata } from '@/shared/queries/metadata'

interface UseIntegrationDomainProps {
  token: string
}

export function useIntegrationDomain(props: UseIntegrationDomainProps) {
  const { token } = props

  const { data: metadata } = useQuery(getMetadata)
  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)

  const endpointHost = new URL(metadata.endpoint).host
  const endpoint = `${endpointHost}/api/${token}/manifest.json`

  const appEndpoint = `stremio://${endpoint}`
  const urlEndpoint = `https://${endpoint}`
  const webEndpoint = `https://web.stremio.com/#/addons?addon=${urlEndpoint}`

  return {
    appEndpoint,
    webEndpoint,
    urlEndpoint,
  }
}
