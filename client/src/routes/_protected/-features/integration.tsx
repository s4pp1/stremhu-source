import {
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'

import { NuvioIntegration } from './nuvio-integration'
import { StremioIntegration } from './stremio-integration'

export function Integration() {
  return (
    <div className="grid gap-4">
      <CardHeader className="px-0">
        <CardTitle>Telepítés</CardTitle>
        <CardDescription>
          Használd a StremHU Source-t a számodra legjobb klienssel.
        </CardDescription>
      </CardHeader>
      <div className="columns-1 md:columns-2 gap-4">
        <div className="break-inside-avoid mb-4">
          <StremioIntegration />
        </div>
        <div className="break-inside-avoid mb-4">
          <NuvioIntegration />
        </div>
      </div>
    </div>
  )
}
