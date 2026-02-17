import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useParams } from '@tanstack/react-router'

import { TokenRegenerate } from '@/features/token-regenerate/token-regenerate'
import { assertExists } from '@/shared/lib/utils'
import { getUser, useRegenerateUserToken } from '@/shared/queries/users'

import { UserProfile } from './-features/user-profile'

export const Route = createFileRoute('/_protected/dashboard/users/$userId/')({
  component: UserRoute,
})

function UserRoute() {
  const { userId } = useParams({ from: '/_protected/dashboard/users/$userId/' })

  const [{ data: user }] = useQueries({
    queries: [getUser(userId)],
  })
  assertExists(user)

  const { mutateAsync: regenerateUserToken } = useRegenerateUserToken()

  const handleRegenerateToken = async () => {
    await regenerateUserToken(user.id)
  }

  return (
    <div className="columns-1 md:columns-2 gap-4">
      <div className="break-inside-avoid mb-4">
        <UserProfile user={user} />
      </div>
      <div className="break-inside-avoid mb-4">
        <TokenRegenerate onSubmit={handleRegenerateToken} />
      </div>
    </div>
  )
}
