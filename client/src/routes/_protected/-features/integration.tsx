import {
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Trans } from '@lingui/react/macro'

import { KodiIntegration } from './kodi-integration'
import { NuvioIntegration } from './nuvio-integration'
import { StremioIntegration } from './stremio-integration'

export function Integration() {
  return (
    <div className="grid gap-4">
      <CardHeader className="px-0">
        <CardTitle><Trans>Supported clients</Trans></CardTitle>
        <CardDescription>
          <Trans>Connect StremHU Source to the clients you use.</Trans>
        </CardDescription>
      </CardHeader>
      <div className="columns-1 md:columns-2 gap-4">
        <div className="break-inside-avoid mb-4">
          <StremioIntegration />
        </div>
        <div className="break-inside-avoid mb-4">
          <NuvioIntegration />
        </div>
        <div className="break-inside-avoid mb-4">
          <KodiIntegration />
        </div>
      </div>
    </div>
  )
}
