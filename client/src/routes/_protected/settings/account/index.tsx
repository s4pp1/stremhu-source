import { createFileRoute } from '@tanstack/react-router'

import { TokenRegenerate } from '@/features/token-regenerate/token-regenerate'
import { useRegenerateMeToken } from '@/shared/queries/me'

import { LoginAndSecurity } from './-features/login-and-security'

export const Route = createFileRoute('/_protected/settings/account/')({
  component: RouteComponent,
})

function RouteComponent() {
  const { mutateAsync: regenerateMeToken } = useRegenerateMeToken()

  const handleRegenerateToken = async () => {
    await regenerateMeToken()
  }

  return (
    <div className="columns-1 md:columns-2 gap-4">
      <div className="break-inside-avoid mb-4">
        <LoginAndSecurity />
      </div>
      <div className="break-inside-avoid mb-4">
        <TokenRegenerate onSubmit={handleRegenerateToken} />
      </div>
    </div>
  )
}
