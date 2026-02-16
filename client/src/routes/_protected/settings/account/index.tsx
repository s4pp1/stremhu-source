import { createFileRoute } from '@tanstack/react-router'

import { LoginAndSecurity } from './-features/login-and-security'
import { TokenRegenerate } from './-features/token-regenerate'

export const Route = createFileRoute('/_protected/settings/account/')({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="columns-1 md:columns-2 gap-4">
      <div className="break-inside-avoid mb-4">
        <LoginAndSecurity />
      </div>
      <div className="break-inside-avoid mb-4">
        <TokenRegenerate />
      </div>
    </div>
  )
}
