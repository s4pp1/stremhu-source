import { createFileRoute } from '@tanstack/react-router'

import { NetworkAccessInfo } from './-features/network-access-info'
import { StremhuCatalogInfo } from './-features/stremhu-catalog-info'
import { Trackers } from './-features/trackers'

export const Route = createFileRoute('/_protected/settings/system/')({
  component: SystemRoute,
})

function SystemRoute() {
  return (
    <div className="columns-1 md:columns-2 gap-4">
      <div className="break-inside-avoid mb-4">
        <Trackers />
      </div>
      <div className="break-inside-avoid mb-4">
        <NetworkAccessInfo />
      </div>
      <div className="break-inside-avoid mb-4">
        <StremhuCatalogInfo />
      </div>
    </div>
  )
}
