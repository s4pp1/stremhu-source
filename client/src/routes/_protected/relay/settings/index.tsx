import { createFileRoute } from '@tanstack/react-router'

import { Connection } from './-features/connection'
import { Port } from './-features/port'
import { Speed } from './-features/speed'

export const Route = createFileRoute('/_protected/relay/settings/')({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="grid gap-4">
      <div className="columns-1 md:columns-2 gap-4">
        <div className="break-inside-avoid mb-4">
          <Port />
        </div>
        <div className="break-inside-avoid mb-4">
          <Speed />
        </div>
        <div className="break-inside-avoid mb-4">
          <Connection />
        </div>
      </div>
    </div>
  )
}
